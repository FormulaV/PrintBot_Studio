package com.example.printuploader

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ImageButton
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView

// Model data sederhana untuk membedakan pengirim
data class ChatMessage(
    val text: String,
    val isUser: Boolean,
    val type: Int = ChatAdapter.TYPE_TEXT,
    val fileName: String = "",
    val fileSize: String = "",
    val fileUrl: String = ""
)

class ChatAdapter(
    private val messageList: ArrayList<ChatMessage>,
    private val onDownloadFile: (ChatMessage) -> Unit = {}
) : RecyclerView.Adapter<RecyclerView.ViewHolder>() {

    companion object {
        const val TYPE_TEXT = 0
        const val TYPE_FILE = 1
        const val TYPE_TYPING = 2
        const val TYPE_BOT_FILE = 3
        const val TYPE_SYSTEM = 4

        private const val VIEW_TYPE_USER_TEXT = 1
        private const val VIEW_TYPE_BOT_TEXT = 2
        private const val VIEW_TYPE_USER_FILE = 3
        private const val VIEW_TYPE_BOT_TYPING = 4
        private const val VIEW_TYPE_BOT_FILE = 5
        private const val VIEW_TYPE_SYSTEM = 6
    }

    override fun getItemViewType(position: Int): Int {
        val message = messageList[position]
        return when {
            message.type == TYPE_SYSTEM -> VIEW_TYPE_SYSTEM
            message.type == TYPE_FILE && message.isUser -> VIEW_TYPE_USER_FILE
            message.type == TYPE_BOT_FILE -> VIEW_TYPE_BOT_FILE
            message.type == TYPE_TYPING -> VIEW_TYPE_BOT_TYPING
            message.isUser -> VIEW_TYPE_USER_TEXT
            else -> VIEW_TYPE_BOT_TEXT
        }
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): RecyclerView.ViewHolder {
        return when (viewType) {
            VIEW_TYPE_USER_TEXT -> {
                val view = LayoutInflater.from(parent.context).inflate(R.layout.item_chat_user, parent, false)
                UserViewHolder(view)
            }
            VIEW_TYPE_USER_FILE -> {
                val view = LayoutInflater.from(parent.context).inflate(R.layout.item_chat_user_file, parent, false)
                UserFileViewHolder(view)
            }
            VIEW_TYPE_BOT_TYPING -> {
                val view = LayoutInflater.from(parent.context).inflate(R.layout.item_chat_bot_typing, parent, false)
                BotTypingViewHolder(view)
            }
            VIEW_TYPE_BOT_FILE -> {
                val view = LayoutInflater.from(parent.context).inflate(R.layout.item_chat_bot_file, parent, false)
                BotFileViewHolder(view)
            }
            VIEW_TYPE_SYSTEM -> {
                val view = LayoutInflater.from(parent.context).inflate(R.layout.item_chat_system, parent, false)
                SystemViewHolder(view)
            }
            else -> {
                val view = LayoutInflater.from(parent.context).inflate(R.layout.item_chat_bot, parent, false)
                BotViewHolder(view)
            }
        }
    }

    override fun onBindViewHolder(holder: RecyclerView.ViewHolder, position: Int) {
        val message = messageList[position]
        when (holder) {
            is UserViewHolder -> holder.tvMessage.text = message.text
            is BotViewHolder -> holder.tvMessage.text = message.text
            is UserFileViewHolder -> {
                holder.tvFileName.text = message.fileName
                holder.tvFileSize.text = message.fileSize
            }
            is BotFileViewHolder -> {
                holder.tvFileName.text = message.fileName
                holder.tvFileSize.text = message.fileSize.ifBlank { "PDF siap diunduh" }
                holder.btnDownload.setOnClickListener { onDownloadFile(message) }
            }
            is BotTypingViewHolder -> holder.tvTyping.text = message.text
            is SystemViewHolder -> holder.tvMessage.text = message.text
        }
    }

    override fun getItemCount(): Int = messageList.size

    class UserViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        val tvMessage: TextView = itemView.findViewById(R.id.tvUserMessage)
    }

    class BotViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        val tvMessage: TextView = itemView.findViewById(R.id.tvBotMessage)
    }

    class UserFileViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        val tvFileName: TextView = itemView.findViewById(R.id.tvFileName)
        val tvFileSize: TextView = itemView.findViewById(R.id.tvFileSize)
    }

    class BotTypingViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        val tvTyping: TextView = itemView.findViewById(R.id.tvTyping)
    }

    class BotFileViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        val tvFileName: TextView = itemView.findViewById(R.id.tvBotFileName)
        val tvFileSize: TextView = itemView.findViewById(R.id.tvBotFileSize)
        val btnDownload: ImageButton = itemView.findViewById(R.id.btnDownloadFile)
    }

    class SystemViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        val tvMessage: TextView = itemView.findViewById(R.id.tvSystemMessage)
    }
}
