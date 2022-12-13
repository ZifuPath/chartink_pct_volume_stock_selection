import datetime
import time
import warnings
import dotenv
import os
import numpy as np
import pandas as pd
import chromedriver_autoinstaller as ca
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from py5paisa import FivePaisaClient

warnings.filterwarnings('ignore')
dotenv.load_dotenv()

def chrome_install(option=None, options=False):
    try:
        if options:
            option.add_argument("--headless")
            option.add_argument('ignore-certificate-errors')
            driver = webdriver.Chrome(executable_path='chromedriver.exe', options=option)
            driver.get("www.google.com")
            driver.close()
        else:
            driver = webdriver.Chrome(executable_path='chromedriver.exe')
            driver.get("www.google.com")
            driver.close()
    except:
        ca.install(cwd=True)
        option.add_argument("--headless")
        option.add_argument('ignore-certificate-errors')
        driver = webdriver.Chrome(executable_path='chromedriver.exe',options=option)
        driver.close()
    return driver


def get_stocks(url):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument('ignore-certificate-errors')
    driver = webdriver.Chrome(executable_path='chromedriver.exe', options=chrome_options)
    driver.get(url)
    stock = []
    try:
        table = driver.find_element(by='xpath',value='//*[@id="DataTables_Table_0"]')
        rows = table.find_element(by='xpath',value='//*[@id="DataTables_Table_0"]/tbody')
        rows = rows.find_elements(by='tag name',value='tr')
        for row in rows:
            cols = row.find_elements(by='tag name',value='td')
            if cols:
                stock.append([col.text for col in cols])
        return stock
    except BaseException as err:
        print(err.args)


def main(url):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument('ignore-certificate-errors')
    chrome_install(options=True, option=chrome_options)
    st = get_stocks(url)
    if len(st)>0:
        df =pd.DataFrame(st,columns=['Sr.no','Name','Symbol','Links','%CH','Price','Vol'])
        feature = ['Name','Symbol','%CH','Price']
        df = df[feature]
        return df
    else:
        return 'No stocks found'


def get_client():
    import ast
    # GET PY5PAISA OBJECT  return py5paisa object
    cred = ast.literal_eval(os.getenv('cred'))
    email = os.getenv('email')
    dob = os.getenv('dob')
    password = os.getenv('passwd')
    client = FivePaisaClient(email=email, passwd=password, dob=dob, cred=cred)
    return client


def telegram_bot_sendtext(bot_message:str):
    #SEND MESSAGE THROUGH TELEGRAM
    bot_token = os.getenv('bot_token')
    bot_chatID = os.getenv('bot_chatID')
    send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + bot_chatID + '&parse_mode=Markdown&text=' + bot_message
    response = requests.get(send_text)
    print(bot_message, response)
    return response.json()


def app():
    url = 'https://chartink.com/screener/1-hour-4-5-12-bullish-3-min-breakout-candle-volume-greater-than-all-previous-volume'
    res = main(url)
    if isinstance(res, str):
        print(res)
    else:
        pass
    alist = list(res.Symbol)
    df = pd.read_csv('dataset/scripmaster-csv-format.csv')
    df = df[df.Name.isin(alist) & (df.Exch == 'N')]
    t1 = datetime.datetime.today().strftime('%Y-%m-%d')
    t2 = datetime.datetime.today().strftime('%Y-%m-%d')
    df = df.reset_index()
    client = get_client()
    client.login()
    for i in df.index:
        print(df.Name.iloc[i])
        data = client.historical_data(Exch=df['Exch'].iloc[i],
                                      ExchangeSegment=df['ExchType'].iloc[i],
                                      ScripCode=df['Scripcode'].iloc[i],
                                      time='1m', From=t2, To=t1)
        if isinstance(data, pd.DataFrame):
            data.Datetime = pd.to_datetime(data.Datetime)
            data = data.set_index('Datetime')
            data = data.resample('3Min').max()
            data = data.head(-1)
            high_day = data[:-2].High.max()
            volume_high = data[:-2].Volume.max()
            # print(high_day, volume_high)
            data['cond'] = np.where((data.Close > high_day) & (data.Volume > volume_high), True, False)
            # print(data.cond.iloc[-1])
            if data.cond.iloc[-1]:
                msg = f"{df.Name.iloc[i]} BUY CONDITION SATISFIED"
                telegram_bot_sendtext(msg)
        time.sleep(1)
        break

if __name__ == '__main__':
    while datetime.datetime.now().time() < datetime.time(10, 0):
        time.sleep(5)
    while datetime.time(10, 0) < datetime.datetime.now().time() < datetime.time(15, 30):
        if datetime.datetime.now().minute % 3 == 0:
            app()
            time.sleep(60)
