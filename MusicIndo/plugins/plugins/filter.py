import re
import datetime
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from MusicIndo import app
from MusicIndo.plugins.utils.error import capture_err
from MusicIndo.plugins.utils.permissions import adminsOnly, member_permissions
from MusicIndo.utils.keyboard import ikb
from .notes import extract_urls
from MusicIndo.utils.functions import (
    check_format,
    extract_text_and_keyb,
    get_data_and_name,
)
from MusicIndo.utils.database import (
    delete_filter,
    deleteall_filters,
    get_filter,
    get_filters_names,
    save_filter,
)

from config import BANNED_USERS


__MODULE__ = "Filters"
__HELP__ = """/fr To Get All The Filters In The Chat.
/fr [FILTER_NAME] To Save A Filter(reply to a message).

Supported filter types are Text, Animation, Photo, Document, Video, video notes, Audio, Voice.

To use more words in a filter use:
/fr Hey_there To filter "Hey there".

/rm [FILTER_NAME] To Stop A Filter.
/rmall To delete all the filters in a chat (permanently).

You can use markdown or html to save text too.

Checkout /markdownhelp to know more about formattings and other syntax.
"""


@app.on_message(filters.command("fr") & ~filters.private & ~BANNED_USERS)
@adminsOnly("can_change_info")
async def save_filters(_, message):
    try:
        if len(message.command) < 2:
            return await message.reply_text(
                "**Usage:** Reply to a message with /fr [FILTER_NAME] to set a new filter."
            )
        replied_message = message.reply_to_message
        if not replied_message:
            replied_message = message
        data, name = await get_data_and_name(replied_message, message)
        if len(name) < 2:
            return await message.reply_text(
                f"The filter name must be greater than 2 characters."
            )
        if data == "error":
            return await message.reply_text(
                "**Usage:** /fr [FILTER_NAME] [CONTENT]\nOr reply to a message with /fr [FILTER_NAME]."
            )

        # Detect message type
        _type, file_id = None, None
        if replied_message.text:
            _type = "text"
        elif replied_message.sticker:
            _type = "sticker"
            file_id = replied_message.sticker.file_id
        elif replied_message.animation:
            _type = "animation"
            file_id = replied_message.animation.file_id
        elif replied_message.photo:
            _type = "photo"
            file_id = replied_message.photo.file_id
        elif replied_message.document:
            _type = "document"
            file_id = replied_message.document.file_id
        elif replied_message.video:
            _type = "video"
            file_id = replied_message.video.file_id
        elif replied_message.video_note:
            _type = "video_note"
            file_id = replied_message.video_note.file_id
        elif replied_message.audio:
            _type = "audio"
            file_id = replied_message.audio.file_id
        elif replied_message.voice:
            _type = "voice"
            file_id = replied_message.voice.file_id

        if replied_message.reply_markup and not re.findall(r"\[.+\,.+\]", data):
            urls = extract_urls(replied_message.reply_markup)
            if urls:
                response = "\n".join(
                    [f"{name}=[{text}, {url}]" for name, text, url in urls]
                )
                data += response

        if data:
            data = await check_format(ikb, data)
            if not data:
                return await message.reply_text("Invalid formatting, check the help section.")

        name = name.replace("_", " ")
        _filter = {
            "type": _type,
            "data": data,
            "file_id": file_id,
        }

        chat_id = message.chat.id
        await save_filter(chat_id, name, _filter)
        await message.reply_text(f"Saved filter '{name}'.")
    except UnboundLocalError:
        await message.reply_text("The replied message is inaccessible. Forward the message and try again.")


@app.on_message(filters.command("frs") & ~filters.private & ~BANNED_USERS)
@capture_err
async def get_filters(_, message):
    filters_list = await get_filters_names(message.chat.id)
    if not filters_list:
        return await message.reply_text("No filters in this chat.")
    
    filters_list.sort()
    msg = f"List of filters in **{message.chat.title}**:\n"
    for f in filters_list:
        msg += f"**-** `{f}`\n"
    await message.reply_text(msg)


@app.on_message(filters.command("rm") & ~filters.private & ~BANNED_USERS)
@adminsOnly("can_change_info")
async def stop_filter(_, message):
    if len(message.command) < 2:
        return await message.reply_text("Usage: /stop [FILTER_NAME]")
    
    filter_name = message.text.split(None, 1)[1].lower().strip()
    _filter = await get_filter(message.chat.id, filter_name)
    
    if not _filter:
        return await message.reply_text("No such filter exists.")
    
    await delete_filter(message.chat.id, filter_name)
    await message.reply_text(f"Stopped filter '{filter_name}'.")


@app.on_message(filters.command("rmall") & ~filters.private & ~BANNED_USERS)
@adminsOnly("can_change_info")
async def stop_all(_, message):
    filters_list = await get_filters_names(message.chat.id)
    if not filters_list:
        return await message.reply_text("No filters in this chat.")
    
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Yes, delete all", callback_data="stop_yes")],
            [InlineKeyboardButton("No, cancel", callback_data="stop_no")],
        ]
    )
    await message.reply_text("Are you sure you want to delete all filters in this chat?", reply_markup=keyboard)


@app.on_callback_query(filters.regex("stop_(.*)") & ~BANNED_USERS)
async def stop_all_cb(_, cb):
    chat_id = cb.message.chat.id
    from_user = cb.from_user
    permissions = await member_permissions(chat_id, from_user.id)
    
    if "can_change_info" not in permissions:
        return await cb.answer("You don't have permission to do this.", show_alert=True)

    action = cb.data.split("_", 1)[1]
    
    if action == "yes":
        await deleteall_filters(chat_id)
        await cb.message.edit("Successfully deleted all filters in this chat.")
    elif action == "no":
        await cb.message.delete()
