import requests, json, datetime
from datetime import datetime
from urllib.parse import urljoin


class Photo:
    name = ''

    def __init__(self, date, likes, sizes):
        self.date = date
        self.likes = likes
        self.sizes = sizes
        self.size_type = sizes['type']
        self.url = sizes['url']
        self.maxsize = max(sizes['width'], sizes['height'])

    def __repr__(self):
        return f'date: {self.date}, likes: {self.likes}, size: {self.maxsize}, url: {self.url}'


class VKUnloader:
    BASE_URL = "https://api.vk.com/method/"

    @staticmethod
    def find_largest(sizes):
        sizes_chart = ['x', 'z', 'y', 'r', 'q', 'p', 'o', 'x', 'm', 's']
        for chart in sizes_chart:
            for size in sizes:
                if size['type'] == chart:
                    return size

    def __init__(self):
        self.token = '958eb5d439726565e9333aa30e50e0f937ee432e927f0dbd541c541887d919a7c56f95c04217915c32008'
        self.version = '5.124'

    def get_photos(self, uid, qty=5):
        get_url = urljoin(self.BASE_URL, 'photos.get')
        resp = requests.get(get_url, params={
            'access_token': self.token,
            'v': self.version,
            'owner_id': uid,
            'album_id': 'profile',
            'photo_sizes': 1,
            'extended': 1
        }).json().get('response').get('items')

        return sorted([Photo(photo.get('date'),
                             photo.get('likes')['count'],
                             self.find_largest(photo.get('sizes'))) for photo in resp],
                      key=lambda p: p.maxsize, reverse=True)[:qty]


class YaUploader:

    @staticmethod
    def create_file_names(photos):
        for photo in photos:
            photo.name = str(photo.likes)
            if [p.likes for p in photos].count(photo.likes) > 1:
                photo.name += '_' + str(photo.date)
            photo.name += '.jpg'

    @staticmethod
    def check_folder_name(n_folder, ex_folders):
        if n_folder not in ex_folders:
            return n_folder
        n = 1
        n_folder += '_' + str(n)
        while n_folder in ex_folders:
            n_folder = n_folder.replace('_' + str(n), '_' + str(n + 1))
            n += 1
        return n_folder

    def __init__(self, token: str):
        self.auth = f'OAuth {token}'

    def get_folders(self):
        return [p['name'] for p in (requests.get("https://cloud-api.yandex.net/v1/disk/resources",
                                                 params={"path": '/'},
                                                 headers={"Authorization": self.auth})
                                    .json().get('_embedded').get('items')) if p['type'] == 'dir']


    def create_folder(self, folder_name):
        resp = requests.put("https://cloud-api.yandex.net/v1/disk/resources",
                            params={"path": '/' + folder_name},
                            headers={"Authorization": self.auth})
        print(f'Создание папки "{folder_name}" ответ сервера:' + str(resp.status_code))
        return resp.ok



    def upload(self, uid, photos):
        upload_folder = self.check_folder_name(uid, self.get_folders())
        self.create_file_names(photos)
        if self.create_folder(upload_folder):
            log_result = []
            for photo in photos:
                response = requests.post("https://cloud-api.yandex.net/v1/disk/resources/upload",
                                         params={"path": '/' + upload_folder + '/' + photo.name,
                                                 "url": photo.url},
                                         headers={"Authorization": self.auth})
                if response.status_code == 202:
                    print(f'Фотография "{photo.name}" загружена!')
                    log_result.append({"file_name": photo.name, "size": photo.size_type})
                else:
                    print(f'Ошибка загрузки фотографии "{photo.name}": '
                          f'{response.json().get("message")}. Status code: {response.status_code}')
            with open(f'{uid}_{datetime.now().strftime("%m_%d_%Y_%H_%M_%S")}_files.json', "w") as f:
                json.dump(log_result, f, ensure_ascii=False, indent=2)


def init():
    ya_token = input('Введите YandexDisk token:')
    uid = input('Введите VK user id:')
    qty = input('Введите количество фотографий для загрузки: ')
    vk_api = VKUnloader()
    ya_api: YaUploader = YaUploader(ya_token)
    ya_api.upload(uid, vk_api.get_photos(uid, int(qty)))


if __name__ == '__main__':
    init()