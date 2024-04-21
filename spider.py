import copy
import time
import pandas as pd
import requests
from lxml import etree
from tqdm import tqdm
from loguru import logger

class MySpider:
    def __init__(self, proxies=None):
        if proxies:
            self.proxies = proxies
        else:
            self.proxies = None
        self.timestamp = str(time.time() * 1000)
        self.base_url = "https://www.fleetnews.co.uk/emissions-data/results"
        self.info_url = "https://www.fleetnews.co.uk/emissions-data/get/{}"
        self.info_struct = {
            "Car_name": "",
            "Id": "",
            "Drive": "",
            "Body_type": "",
            "Transmission": "",
            "Engine(Litres)": "",
            "Power": "",
            "Predicted_fuel_economy": "",
            "Official_WLTP_mpg": "",

        }

        self.info_list = []

    def get_id(self):

        for year in ['2020','2021','2022','2023']:
            for num in range(1,100):
                try:
                    params = {
                        "ManufacturerId": "",
                        "ModelGroupId": "",
                        "ManufacturerName": "",
                        "ModelName": "",
                        "Year": year,
                        "BodyStyle": "Estate",
                        "Engine": "",
                        "CO2Rating": "",
                        "UrbanNoxRating": "",
                        "SearchTerm": "",
                        "SortBy": "ModelYear",
                        "SortDesc": "True",
                        "P": str(num),
                        "_": self.timestamp
                    }
                    response = requests.get(url=self.base_url, params=params, proxies=self.proxies)
                    html = etree.HTML(response.text)
                    id_list = html.xpath('//a[@class="data-more-details"]')
                    if id_list == []:
                        break
                    for i in id_list:
                        car_name = i.xpath('./strong/text()')[0].replace(' ', '')
                        tmp_info = copy.deepcopy(self.info_struct)
                        tmp_info['Car_name'] = car_name.replace('\n', ' ')
                        tmp_info['Id'] = i.xpath('./@data-item-id')[0]
                        tmp_info['Year'] = year
                        self.info_list.append(tmp_info)
                    print(f'finish{num}Page data collection.')
                except:
                    print(f'{num}Page data collection failed!')

    def get_data(self, info_body):
        params = {
            "_": self.timestamp
        }
        response = requests.get(url=self.info_url.format(info_body['Id']), params=params, proxies=self.proxies)
        response_json = response.json()
        info_body['Drive'] = response_json['driveTrain']
        info_body['Body_type'] = response_json['bodyStyle']
        info_body['Transmission'] = response_json['transmission']
        info_body['Engine(Litres)'] = response_json['engineL']
        info_body['Power'] = str(response_json['powerPS']) + ' bhp'
        info_body['Predicted_fuel_economy'] = str(response_json['airMpg']) + ' mpg' + '\n' + str(
            round(response_json['fuelEconomy'], 1)) + " litres/100km"
        info_body['Official_WLTP_mpg'] = str(response_json['officialWltpMpg']) + ' mpg'
        info_body['OfficialCO2'] = str(response_json['officialCO2'])
        info_body['FuelType'] = str(response_json['fuelType'])
        info_body['ManufacturerName'] = str(response_json['manufacturerName'])
        info_body['ModelName'] = str(response_json['modelName'])

    def save(self):
        df = pd.DataFrame(self.info_list)
        df.to_csv("car_data.csv", index=False)

    def run(self):
        self.get_id()
        for i in tqdm(self.info_list):
            try:
                self.get_data(i)
            except:
                logger.info(i, "Error, please handle separately")
        self.save()


if __name__ == '__main__':
    spider = MySpider({'http': 'http://127.0.0.1:10809'})
    spider.run()
