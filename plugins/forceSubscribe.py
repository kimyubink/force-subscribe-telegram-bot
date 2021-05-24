import time
import logging
from Config import Config
from pyrogram import Client, filters
from sql_helpers import forceSubscribe_sql as sql
from pyrogram.types import ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant, UsernameNotOccupied, ChatAdminRequired, PeerIdInvalid

logging.basicConfig(level=logging.INFO)

static_data_filter = filters.create(lambda _, __, query: query.data == "onUnMuteRequest")
@Client.on_callback_query(static_data_filter)
def _onUnMuteRequest(client, cb):
  user_id = cb.from_user.id
  chat_id = cb.message.chat.id
  chat_db = sql.fs_settings(chat_id)
  if chat_db:
    channel = chat_db.channel
    chat_member = client.get_chat_member(chat_id, user_id)
    if chat_member.restricted_by:
      if chat_member.restricted_by.id == (client.get_me()).id:
          try:
            client.get_chat_member(channel, user_id)
            client.unban_chat_member(chat_id, user_id)
            if cb.message.reply_to_message.from_user.id == user_id:
              cb.message.delete()
          except UserNotParticipant:
            client.answer_callback_query(cb.id, text="❗ Entre no canal mencionado e precione 'Remover Silêncio!' novamente.", show_alert=True)
      else:
        client.answer_callback_query(cb.id, text="❗ Você foi silenciado pelos administradores por outro motivo.", show_alert=True)
    else:
      if not client.get_chat_member(chat_id, (client.get_me()).id).status == 'administrator':
        client.send_message(chat_id, f"❗ **{cb.from_user.mention} está tentando retirar seu próprio silêncio, mas não consigo reativá-lo porque não sou um admin deste chat! Me coloque como um administrador. **\n__#Saindo do grupo...__")
        client.leave_chat(chat_id)
      else:
        client.answer_callback_query(cb.id, text="❗ Atenção: não clique no botão se pode conversar livremente!", show_alert=True)



@Client.on_message(filters.text & ~filters.private & ~filters.edited, group=1)
def _check_member(client, message):
  chat_id = message.chat.id
  chat_db = sql.fs_settings(chat_id)
  if chat_db:
    user_id = message.from_user.id
    if not client.get_chat_member(chat_id, user_id).status in ("administrator", "creator") and not user_id in Config.SUDO_USERS:
      channel = chat_db.channel
      try:
        client.get_chat_member(channel, user_id)
      except UserNotParticipant:
        try:
          sent_message = message.reply_text(
              "{}, você **não é inscrito** ao meu [canal](https://t.me/{}) ainda. Por favor, [entre](https://t.me/{}) e **pressione o botão abaixo** para remover o seu silêncio.".format(message.from_user.mention, channel, channel),
              disable_web_page_preview=True,
              reply_markup=InlineKeyboardMarkup(
                  [[InlineKeyboardButton("Remover Silêncio!", callback_data="onUnMuteRequest")]]
              )
          )
          client.restrict_chat_member(chat_id, user_id, ChatPermissions(can_send_messages=False))
        except ChatAdminRequired:
          sent_message.edit("❗ **Não sou admin aqui.**\n__Me adicione novamente e me faça um administrador com permissão de banir usuários.\n#Saindo do grupo...__")
          client.leave_chat(chat_id)
      except ChatAdminRequired:
        client.send_message(chat_id, text=f"❗ **Não sou admin neste canal: @{channel}.**\n__Me faça um administrador e me adicione novamente.\n#Saindo do grupo...__")
        client.leave_chat(chat_id)


@Client.on_message(filters.command(["forcesubscribe", "fsub"]) & ~filters.private)
def config(client, message):
  user = client.get_chat_member(message.chat.id, message.from_user.id)
  if user.status is "creator" or user.user.id in Config.SUDO_USERS:
    chat_id = message.chat.id
    if len(message.command) > 1:
      input_str = message.command[1]
      input_str = input_str.replace("@", "")
      if input_str.lower() in ("off", "não", "desabilitado"):
        sql.disapprove(chat_id)
        message.reply_text("❌ **Forçar inscrição desativado com sucesso.**")
      elif input_str.lower() in ('clear'):
        sent_message = message.reply_text('**Removendo silêncio de todos os membros silenciados por mim...**')
        try:
          for chat_member in client.get_chat_members(message.chat.id, filter="restricted"):
            if chat_member.restricted_by.id == (client.get_me()).id:
                client.unban_chat_member(chat_id, chat_member.user.id)
                time.sleep(1)
          sent_message.edit('✅ **Silêncio de todos os usuários mutados por mim removido.**')
        except ChatAdminRequired:
          sent_message.edit('❗ **Não sou admin neste grupo.**\n__Eu não posso silenciar/remover o silêncio porque não sou admin! Me faça um administrador e tente novamente.__')
      else:
        try:
          client.get_chat_member(input_str, "me")
          sql.add_channel(chat_id, input_str)
          message.reply_text(f"✅ **Forçar inscrição ativado com sucesso!**\n__Forçar inscrição está ativado, todos os membros do grupo precisam se inscrever neste [canal](https://t.me/{input_str}) obrigatoriamente para enviar mensagens neste grupo.__", disable_web_page_preview=True)
        except UserNotParticipant:
          message.reply_text(f"❗ **Não sou administrador no canal!**\n__Eu não sou adminstrador no [canal](https://t.me/{input_str}). Me faça um admin para ativar 'Forçar Inscrição'.__", disable_web_page_preview=True)
        except (UsernameNotOccupied, PeerIdInvalid):
          message.reply_text(f"❗ **Nome de usuário do canal inválido.**")
        except Exception as err:
          message.reply_text(f"❗ **ERRO:** ```{err}```")
    else:
      if sql.fs_settings(chat_id):
        message.reply_text(f"✅ **Forçar inscrição foi ativo neste grupo.**\n__Para este [canal](https://t.me/{sql.fs_settings(chat_id).channel})__", disable_web_page_preview=True)
      else:
        message.reply_text("❌ **Forçar inscrição foi desativado neste grupo.**")
  else:
      message.reply_text("❗ **Criador do Grupo obrigatório!**\n__Você precisa ser o criador do grupo para fazer isto..__")
