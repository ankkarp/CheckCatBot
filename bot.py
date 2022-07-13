import logging

from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import os.path
import argparse

from Parser import ParserVK

parser = argparse.ArgumentParser()
parser.add_argument('-a', '--vk_api_token', type=str, help='vk токен')
parser.add_argument('-b', '--bot_token', default='5376821545:AAEh44iTkHZBqKo4Sv2KzyWIawD-rXm6GBM', type=str,
                    help='токен бота')
parser.add_argument('-v', '--verbose', default=True, type=bool, help='выводить прогресс сборки картинок пользователю')
parser.add_argument('-c', '--comments', default=False, type=bool, help='парсить комментарии')
parser.add_argument('-t', '--delay', default=340000, type=int,
                    help='минимальное время между запросами (в микросекундах)')

args = parser.parse_args()


vkparser = ParserVK(args.vk_api_token, args.verbose, args.comments, args.delay)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=args.bot_token)
dp = Dispatcher(bot)


groups = InlineKeyboardMarkup()
group_1 = InlineKeyboardButton(text='Москва', callback_data="podslushanomoskwa")
group_2 = InlineKeyboardButton(text='Санкт-Петербург', callback_data="sbpears")
group_3 = InlineKeyboardButton(text='Екатеринбург', callback_data="podsekb")
groups.add(group_1, group_2, group_3)

okay = InlineKeyboardMarkup()
ok = InlineKeyboardButton(text='Ок', callback_data="ok")
okay.add(ok)


@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    """
    Обрвботчик начальной комманды
    """
    await message.reply("Здравствуйте! Я - бот, считающий процент содержния котов в группах Подслушано городов."
                        "\nВыберите город.", reply_markup=groups)


@dp.callback_query_handler(lambda call: call.data == 'ok')
async def delete_message(call: types.CallbackQuery):
    await bot.delete_message(call.message.chat.id, call.message.message_id)


@dp.callback_query_handler(lambda call: call.data in ["podslushanomoskwa", "sbpears", "podsekb"])
async def menu(call: types.CallbackQuery):
    """
    Обработчик комманд клавиатуры
    """
    if os.path.exists(f'{call.message.chat.id}.jpg'):
        await bot.send_message(call.message.chat.id,'Подождите результатов', reply_markup=okay)
    else:
        # await bot.send_message(call.message.chat.id, f'Выбрана группа vk.com/{call.data}.')
        res = await vkparser.parse_posts(call)
        if os.path.exists(f'{call.message.chat.id}.jpg'):
            os.remove(f'{call.message.chat.id}.jpg')
        if res:
            await bot.send_message(call.message.chat.id, f'В группе vk.com/{call.data} {res * 100}% картинок с котами.')
        else:
            await bot.send_message(call.message.chat.id, f'Возникла ошибка')


if __name__ == "__main__":
    for f in os.listdir('.'):
        if f[f.rfind("."):] == ".jpg":
            os.remove(f)
    executor.start_polling(dp, skip_updates=True)




