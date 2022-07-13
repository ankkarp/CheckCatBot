import os
import time
from datetime import datetime, timedelta

import requests
import vk_requests
from aiogram import types
import asyncio

from model.predict import img_predict


class ParserVK:
    """Класс парсера, отвечающий за парсинг данных, классификацию их."""

    def __init__(self, vk_token: str, verbose: bool, check_comments: bool, delay: int):
        """
        Конструктор парсера

        Параметры:
            vk_token: str
                токен vk api
            verbose: bool
                нужно ли выводить прогресс сборки картинок пользователю
            check_comments: bool
                нужно ли парсить комментарии
            delay: float
                минимальное время между запросами (в микросекундах)
        """
        self.api = vk_requests.create_api(service_token=vk_token)
        self.verbose = verbose
        self.check_comments = check_comments
        self.min_time = time.mktime((2022, 1, 1, 0, 0, 0, 0, 0, 0))
        self.last_request = None
        self.delay = timedelta(microseconds=delay)

    async def classify_photos(self, call, cats, total, post: dict):
        """
        Метод классификации картинок по признаку наличия на них кошок

        Параметры:
            call: aiogram.types.CallbackQuery
                запрос к боту
            cats: int
                кол-во картинок с котами
            total:
                кол-во картинок с котами
            post: dict
                словарь с данными о посте в группе вк

        Ничего не возвращает
        """
        if "attachments" in post.keys():
            for f in post["attachments"]:
                if f["type"] == "photo":
                    try:
                        with open(f'{call.message.chat.id}.jpg', 'wb') as img_file:
                            img_file.write(requests.get(f['photo']['sizes'][-1]['url']).content)
                            total += 1
                            cats += int(img_predict(f'{call.message.chat.id}.jpg')[1] == 'Cat')
                    except Exception as e:
                        print(f"{call.message.chat.id}: {e} with {f['photo']['sizes'][-1]['url']}")
        return cats, total

    async def parse_comments(self, call: types.CallbackQuery, cats: int, total: int, post_id: int, owner_id: int,
                             count: int):
        """
        Метод парсинга постов группы за 2022 год.

        Параметры:
            call: aiogram.types.CallbackQuery
                запрос к боту
            cats: int
                кол-во картинок с котами
            total:
                кол-во картинок с котами
            post_id: int
                идентификатор поста группы
            owner_id: int
                индентификатор сообщества
            count: int
                кол-во комментариев

        Ничего не возвращает
        """
        offset = 0
        while offset < count:
            try:
                await self.sleep()
                comments = self.api.wall.getComments(owner_id=owner_id, post_id=post_id, count=100, offset=offset)[
                    'items']
                for comm in comments:
                    cats, total = await self.classify_photos(call, cats, total, comm)
                offset += 100
            except Exception as e:
                print(f'{call.message.chat.id}: {e}')
        return cats, total

    async def sleep(self):
        # print(self.last_request)
        if datetime.now() - self.last_request < self.delay:
            self.last_request += self.delay
            time.sleep((self.last_request - datetime.now()).microseconds / 1e6)
        else:
            self.last_request = datetime.now()

    async def parse_posts(self, call: types.CallbackQuery):
        """
        Метод парсинга постов

        Параметры:
            call: aiogram.types.CallbackQuery
                запрос к боту

        Возвращаемое значение:
            double
                Процентное соотношение кол-ва картинок с котами к общему кол-ву картинок в группе
        """
        offset = 0
        count = 100
        start = datetime.now()
        owner_id = None
        cats = 0
        total = 0
        try:
            while True:
                if self.last_request is None:
                    self.last_request = datetime.now()
                else:
                    await self.sleep()
                posts = self.api.wall.get(domain=call.data, count=count, offset=offset)['items']
                if posts and owner_id is None:
                    owner_id = posts[0]["owner_id"]
                if not posts:
                    return cats / total
                offset += 100
                for p in posts:
                    if p["date"] < self.min_time:
                        if "is_pinned" in p.keys() and p["is_pinned"]:
                            continue
                        else:
                            return cats / total
                    cats, total = await self.classify_photos(call, cats, total, p)
                    if p["comments"] and self.check_comments:
                        cats, total = await self.parse_comments(call, cats, total, p["id"], p['owner_id'],
                                                                p["comments"]["count"])
                if total and self.verbose:
                    await call.message.edit_text(f'Выбрана группа vk.com/{call.data}. Прошло '
                                                 f'{(datetime.now() - start).seconds // 60} мин'
                                                 f'\nОбработано {total} картинок, на '
                                                 f'{cats / total * 100 :0.4f}% из них обнаружены коты.')
        except (Exception, KeyboardInterrupt) as e:
            print(f'{call.message.chat.id}: {e}')
            if os.path.exists(f'{call.message.chat.id}.jpg'):
                os.remove(f'{call.message.chat.id}.jpg')
