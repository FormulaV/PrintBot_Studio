import json
import pickle
import random
import argparse
import sys
import time
from pathlib import Path

import numpy as np
import tensorflow as tf
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
from tensorflow.keras.layers import Bidirectional, Dense, Dropout, Embedding, Input, LSTM, SpatialDropout1D
from tensorflow.keras.models import Sequential
from tensorflow.keras.utils import pad_sequences
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.utils import to_categorical


BASE_DIR = Path(__file__).resolve().parent
DATASET_PATH = BASE_DIR / "dataset_chatbot.json"
MODEL_PATH = BASE_DIR / "chatbot_rnn_model.h5"
TOKENIZER_PATH = BASE_DIR / "tokenizer.pickle"
CLASSES_PATH = BASE_DIR / "classes.pickle"

# Nilai max_len harus sama dengan yang dipakai di app.py pada route /chat.
MAX_LEN = 35
VOCAB_SIZE = 20000
EMBEDDING_DIM = 128
OOV_TOKEN = "<OOV>"
RANDOM_SEED = 42
EPOCHS = 12
BATCH_SIZE = 512
CONFIDENCE_THRESHOLD = 0.6
FINAL_MODEL_PATH = BASE_DIR / f"chatbot_rnn_model_final_epoch_{EPOCHS}.h5"


def normalize_text(text):
    import re
    text = str(text or "").strip().lower()
    # Collapse repeating letters (e.g., "hiii" -> "hi", "hayyy" -> "hay")
    text = re.sub(r'([a-zA-Z])\1+', r'\1', text)
    # Common variations of greetings normalized to standard
    text = re.sub(r'\b(hay|hey|hei|he|hlo|halo|helo|hello)\b', 'hai', text)
    return " ".join(text.split())


def load_dataset():
    with DATASET_PATH.open(encoding="utf-8") as file:
        data = json.load(file)

    sentences = []
    labels = []
    classes = []

    for intent in data.get("intents", []):
        tag = intent.get("tag")
        patterns = intent.get("patterns", [])

        if not tag:
            continue

        if tag not in classes:
            classes.append(tag)

        for pattern in patterns:
            cleaned_pattern = normalize_text(pattern)
            if cleaned_pattern:
                sentences.append(cleaned_pattern)
                labels.append(tag)

    if not sentences:
        raise ValueError("Dataset kosong. Pastikan dataset_chatbot.json memiliki intents dan patterns.")

    return sentences, labels, classes


def build_model(class_count):
    model = Sequential(
        [
            Input(shape=(MAX_LEN,)),
            Embedding(VOCAB_SIZE, EMBEDDING_DIM, mask_zero=True),
            SpatialDropout1D(0.2),
            Bidirectional(LSTM(128, return_sequences=True, dropout=0.2)),
            Bidirectional(LSTM(64, dropout=0.2)),
            Dense(128, activation="relu"),
            Dropout(0.35),
            Dense(64, activation="relu"),
            Dropout(0.25),
            Dense(class_count, activation="softmax"),
        ]
    )

    model.compile(
        loss="categorical_crossentropy",
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.0008, clipnorm=1.0),
        metrics=["accuracy"],
    )
    return model


def get_response(model, tokenizer, classes, data, message, threshold=CONFIDENCE_THRESHOLD):
    cleaned_message = normalize_text(message)
    sequence = tokenizer.texts_to_sequences([cleaned_message])
    padded = pad_sequences(
        sequence,
        maxlen=MAX_LEN,
        padding="post",
        truncating="post",
    )

    prediction = model.predict(padded, verbose=0)[0]
    max_index = int(np.argmax(prediction))
    confidence = float(prediction[max_index])
    tag = classes[max_index]

    if confidence < threshold:
        return {
            "tag": "fallback",
            "confidence": confidence,
            "response": "Maaf, Cetakin Dong belum mengerti maksud kakak. Bisa diulangi?",
        }

    for intent in data.get("intents", []):
        if intent.get("tag") == tag:
            return {
                "tag": tag,
                "confidence": confidence,
                "response": random.choice(intent.get("responses", ["Ada kesalahan pada dataset."])),
            }

    return {
        "tag": tag,
        "confidence": confidence,
        "response": "Ada kesalahan pada sistem.",
    }


def run_terminal_chat_test(model, tokenizer, classes, data):
    print("\n=== Uji Chatbot di Terminal ===")
    print("Ketik pesan untuk mencoba chatbot.")
    print("Ketik 'exit', 'quit', atau 'keluar' untuk berhenti.\n")

    while True:
        try:
            user_message = input("Anda: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSesi uji chatbot selesai.")
            break

        if user_message.lower() in {"exit", "quit", "keluar"}:
            print("Sesi uji chatbot selesai.")
            break

        if not user_message:
            continue

        result = get_response(model, tokenizer, classes, data, user_message)
        print(f"Tag: {result['tag']} | Confidence: {result['confidence']:.4f}")
        print(f"Bot: {result['response']}\n")


class ConsoleProgressBarCallback(tf.keras.callbacks.Callback):
    def on_epoch_begin(self, epoch, logs=None):
        self.epoch = epoch + 1
        self.start_time = time.time()
        print(f"Epoch {self.epoch}/{self.params.get('epochs', '?')}")
        
    def on_batch_end(self, batch, logs=None):
        logs = logs or {}
        batch_count = self.params.get('steps', 1)
        current_step = batch + 1
        
        bar_len = 15
        filled_len = int(bar_len * current_step // batch_count)
        bar = '=' * filled_len
        if filled_len < bar_len:
            bar += '>' + '.' * (bar_len - filled_len - 1)
            
        loss = logs.get('loss', 0.0)
        accuracy = logs.get('accuracy', 0.0)
        
        elapsed = time.time() - self.start_time
        eta = (elapsed / current_step) * (batch_count - current_step) if current_step > 0 else 0
        
        if eta > 60:
            eta_str = f"{int(eta//60)}m{int(eta%60)}s"
        else:
            eta_str = f"{int(eta)}s"
            
        status_line = f"\r{current_step}/{batch_count} [{bar}] - ETA: {eta_str} - loss: {loss:.4f} - accuracy: {accuracy:.4f}"
        
        sys.stdout.write(status_line)
        sys.stdout.flush()

    def on_epoch_end(self, epoch, logs=None):
        logs = logs or {}
        val_loss = logs.get('val_loss')
        val_accuracy = logs.get('val_accuracy')
        elapsed = time.time() - self.start_time
        
        if elapsed > 60:
            elapsed_str = f"{int(elapsed//60)}m{int(elapsed%60)}s"
        else:
            elapsed_str = f"{int(elapsed)}s"
            
        loss = logs.get('loss', 0.0)
        accuracy = logs.get('accuracy', 0.0)
        batch_count = self.params.get('steps', 1)
        
        status_line = f"\r{batch_count}/{batch_count} [{'=' * 15}] - {elapsed_str} - loss: {loss:.4f} - accuracy: {accuracy:.4f}"
        if val_loss is not None and val_accuracy is not None:
            status_line += f" - val_loss: {val_loss:.4f} - val_accuracy: {val_accuracy:.4f}"
            
        sys.stdout.write('\r' + ' ' * 120 + '\r')
        sys.stdout.write(status_line + '\n')
        sys.stdout.flush()


def main():
    parser = argparse.ArgumentParser(description="Train Cetakin Dong RNN model.")
    parser.add_argument("--chat-test", action="store_true", help="Buka mode uji chat interaktif setelah training.")
    args = parser.parse_args()

    random.seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)
    tf.random.set_seed(RANDOM_SEED)

    print("Memuat dataset chatbot...")
    with DATASET_PATH.open(encoding="utf-8") as file:
        data = json.load(file)

    sentences, labels, classes = load_dataset()
    print(f"Jumlah tag: {len(classes)}")
    print(f"Jumlah pattern: {len(sentences)}")

    label_mapping = {tag: index for index, tag in enumerate(classes)}
    encoded_labels = np.array([label_mapping[label] for label in labels])
    categorical_labels = to_categorical(encoded_labels, num_classes=len(classes))

    tokenizer = Tokenizer(num_words=VOCAB_SIZE, oov_token=OOV_TOKEN, lower=True)
    tokenizer.fit_on_texts(sentences)

    sequences = tokenizer.texts_to_sequences(sentences)
    padded_sequences = pad_sequences(
        sequences,
        maxlen=MAX_LEN,
        padding="post",
        truncating="post",
    )

    indices = np.arange(len(padded_sequences))
    np.random.shuffle(indices)
    padded_sequences = padded_sequences[indices]
    categorical_labels = categorical_labels[indices]

    model = build_model(len(classes))

    callbacks = [
        ConsoleProgressBarCallback(),
        EarlyStopping(
            monitor="val_accuracy",
            patience=2,
            restore_best_weights=True,
            verbose=1,
        ),
        ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.5,
            patience=5,
            min_lr=0.00001,
            verbose=1,
        ),
        ModelCheckpoint(
            filepath=str(MODEL_PATH),
            monitor="val_accuracy",
            save_best_only=True,
            verbose=1,
        ),
    ]

    print("Mulai melatih model chatbot berbasis RNN/BiLSTM...")
    print(f"Training membaca semua pattern dataset, lalu berjalan full {EPOCHS} epoch. Early stopping dinonaktifkan.")
    print(f"Model terbaik berdasarkan validation accuracy akan disimpan ke: {MODEL_PATH}")
    history = model.fit(
        padded_sequences,
        categorical_labels,
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        validation_split=0.10,
        shuffle=True,
        callbacks=callbacks,
        verbose=0,
    )

    model.save(FINAL_MODEL_PATH)
    with TOKENIZER_PATH.open("wb") as handle:
        pickle.dump(tokenizer, handle, protocol=pickle.HIGHEST_PROTOCOL)
    with CLASSES_PATH.open("wb") as handle:
        pickle.dump(classes, handle, protocol=pickle.HIGHEST_PROTOCOL)

    final_accuracy = history.history.get("accuracy", [0])[-1]
    final_val_accuracy = history.history.get("val_accuracy", [0])[-1]

    best_model = tf.keras.models.load_model(MODEL_PATH)

    print("Model chatbot berhasil dilatih dan disimpan.")
    print(f"Training accuracy terakhir: {final_accuracy:.4f}")
    print(f"Validation accuracy terakhir: {final_val_accuracy:.4f}")
    print(f"Model terbaik untuk app.py: {MODEL_PATH}")
    print(f"Model hasil epoch terakhir: {FINAL_MODEL_PATH}")
    print(f"Tokenizer: {TOKENIZER_PATH}")
    print(f"Classes: {CLASSES_PATH}")

    if args.chat_test:
        run_terminal_chat_test(best_model, tokenizer, classes, data)


if __name__ == "__main__":
    main()
