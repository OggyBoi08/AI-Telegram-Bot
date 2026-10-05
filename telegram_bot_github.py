from typing import Final
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ConversationHandler, filters, ContextTypes
from telegramify_markdown import convert, split_entities
from groq import Groq
import os
import json
from io import BytesIO

BOT_TOKEN: Final = "<BotToken>"
BOT_USERNAME: Final = "@<YourBotName>"
BOT_PROMPT: Final = "You are a helpful assistant."
LLM_MODEL: Final = "openai/gpt-oss-120b"       #Change it to any model in your GROQ ACCOUNT 
MEMORY_LOCATION: Final = "llm_memory.json"
ATTENTION_WINDOW: Final = 10

WAITING_FOR_MEMORY: Final = 0
WAITING_FOR_INPUT: Final = 1

#initialize groq
groq_client = Groq(
    api_key=os.environ.get("GROQ_API_KEY")    #Your groq API KEY needs to be an environmental variable
)
print("*** GROQ SUCCESSFULLY INITIALIZED ***")

#Utility (not for telegram)
def load_knowledge_base(file_path: str) -> dict:
    with open(file_path,"r") as file:
        data: dict = json.load(file)
    return data

def save_knowledge_base(file_path: str, data: dict):
    with open(file_path,"w") as file:
        json.dump(data, file, indent=2)   #two character space used for indentation

#Commands
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello there!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Help is arriving soon! 🚒🚨")

async def display_memory_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    knowledge_base: dict = load_knowledge_base(MEMORY_LOCATION)
    chat_id: str = str(update.message.chat_id)
    knowledge = knowledge_base[chat_id]
    memories = knowledge["long_term_memory"]
    memory_text = "\n".join(f"{index}. {memory['content']}" for index,memory in enumerate(knowledge["long_term_memory"],1))
    await update.message.reply_text("LONG TERM MEMORY\n-------------------------------\n"+memory_text)

async def delete_memory_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    knowledge_base: dict = load_knowledge_base(MEMORY_LOCATION)
    chat_id: str = str(update.message.chat_id)
    knowledge = knowledge_base[chat_id]
    memories = knowledge["long_term_memory"]
    memory_text = "\n".join(f"{index}. {memory['content']}" for index,memory in enumerate(knowledge["long_term_memory"],1))
    await update.message.reply_text("LONG TERM MEMORY\n-------------------------------\n"+memory_text+"\n\nPlease choose the index to be deleted or type 'skip' to cancel: ")

    return WAITING_FOR_INPUT

async def recieve_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message_type: str = update.message.chat.type  
    text: str = update.message.text    
    chat_id = str(update.message.chat_id)
    knowledge_base: dict = load_knowledge_base(MEMORY_LOCATION)
    knowledge = knowledge_base[chat_id]

    if message_type == "group":
        if BOT_USERNAME in text:
            text = text.replace(BOT_USERNAME,'').strip()
        else:
            return ConversationHandler.END

    if (text == "skip"):
        await update.message.reply_text("continue talking...")
        return ConversationHandler.END

    try:
        index = int(text)
    except ValueError:
        await update.message.reply_text("*Input is not a number")
        return WAITING_FOR_INPUT

    if (index<1 or index>knowledge["memory_len"]):
        await update.message.reply_text("*Index out of range")
        return WAITING_FOR_INPUT

    deleted_memory = knowledge["long_term_memory"].pop(index-1)
    knowledge["memory_len"]-=1;
    for index, memory in enumerate(knowledge["long_term_memory"],1):
        memory["id"] = index
    save_knowledge_base(MEMORY_LOCATION, knowledge_base)
    await update.message.reply_text(f"Memory: [{deleted_memory['content']}] Was Deleted")
    return ConversationHandler.END
    

async def save_memory_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:

    await update.message.reply_text(
        "What should I remember?"
    )

    return WAITING_FOR_MEMORY

async def receive_memory(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message_type: str = update.message.chat.type  
    text: str = update.message.text    
    chat_id = str(update.message.chat_id)
    knowledge_base: dict = load_knowledge_base(MEMORY_LOCATION)
    knowledge = knowledge_base[chat_id]

    if message_type == "group":
        if BOT_USERNAME in text:
            text = text.replace(BOT_USERNAME,'').strip()
        else:
            return ConversationHandler.END

    knowledge["memory_len"]+=1
    knowledge["long_term_memory"].append({
        "id": knowledge["memory_len"],
        "content": text
    })
    save_knowledge_base(MEMORY_LOCATION, knowledge_base)

    await update.message.reply_text(
        "Memory saved! 🧠"
    )

    return ConversationHandler.END
    
    

#Responses

def handle_responses(text: str, knowledge: dict):  #handles message logic
    processed_text = text.strip()
    memory_text = "\n".join(f"- {memory['content']}" for memory in knowledge["long_term_memory"])
    messages: list = [
            {
                "role": "system",
                "content": BOT_PROMPT + "\n\nLong Term Memory About The User: \n" + memory_text 
            }
    ]

    messages.extend(knowledge["conversation"])
    messages.append({
        "role": "user",
        "content": processed_text
    })

    groq_response = groq_client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages
    )

    markdown = groq_response.choices[0].message.content;
    #messages = await telegramify(markdown, max_message_length=4090)
    formatted_text, entities = convert(markdown)
    #entities=[MessageEntity(type="bold", offset=0, length=5)]

    return formatted_text, entities, markdown


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_type: str = update.message.chat.type  #check if message is a group message or a private message
    text: str = update.message.text    #incoming message
    knowledge_base: dict = load_knowledge_base(MEMORY_LOCATION)
    chat_id = str(update.message.chat_id)

    if chat_id not in knowledge_base:
        knowledge_base[chat_id] = {
            "memory_len": 0,
            "long_term_memory": [],
            "conversation": []
        }
        
    knowledge = knowledge_base[chat_id]

    print(f"user: {update.message.chat.id} in {message_type}: {text}")

    if message_type == "group":
        if BOT_USERNAME in text:
            text = text.replace(BOT_USERNAME,'').strip()
            messages, entities, markdown = handle_responses(text, knowledge)
        else:
            return
    else:
        messages, entities, markdown = handle_responses(text, knowledge)

    knowledge["conversation"].append({
        "role": "user",
        "content": text
    })

    print("Bot:",markdown)
    for chunk_text, chunk_entities in split_entities(messages, entities, max_utf16_len=4096):
        await update.message.reply_text(
            chunk_text,
            entities=[e.to_dict() for e in chunk_entities],
        )

    knowledge["conversation"].append({
        "role": "assistant",
        "content": markdown
    })
    knowledge["conversation"] = knowledge["conversation"][-ATTENTION_WINDOW:]
    save_knowledge_base(MEMORY_LOCATION, knowledge_base)
    
    

async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Update: {update} caused error: {context.error}")

if __name__ == "__main__":    #Run this code only if it is being executed from the main
    print("Starting bot...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    #Conversation handler
    save_memory_handler = ConversationHandler(
        entry_points=[
            CommandHandler("save_memory", save_memory_command)
        ],

        states={
            WAITING_FOR_MEMORY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_memory)
            ]
        },

        fallbacks=[]
    )

    delete_memory_handler = ConversationHandler(
        entry_points=[CommandHandler("delete_memory", delete_memory_command)
        ],

        states={
            WAITING_FOR_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, recieve_input)
            ]
        },

        fallbacks=[]
    )

    #Commands
    app.add_handler(CommandHandler("start",start_command))
    app.add_handler(CommandHandler("help",help_command))
    app.add_handler(CommandHandler("display_memory",display_memory_command))
    app.add_handler(save_memory_handler)
    app.add_handler(delete_memory_handler)

    #Message
    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    #Errors
    app.add_error_handler(error)

    print("Polling...")
    app.run_polling(poll_interval=5)
