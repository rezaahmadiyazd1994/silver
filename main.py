from asyncio.windows_events import NULL
from contextlib import nullcontext
from ftplib import parse150
import json
import requests
from bs4 import BeautifulSoup
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from keras.models import model_from_json
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from textblob import TextBlob
from nltk.corpus import stopwords
import os
from datetime import datetime
from abc import ABC, abstractmethod
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


global sell_counter,buy_counter
sell_counter = 0
buy_counter = 0

class Model_Data(ABC):

    @abstractmethod
    def load_data(self,csv_path):
        pass

    @abstractmethod
    def data_preprocessing(self,drop_list):
        pass

    @abstractmethod
    def load_model(self,path_json,path_h5):
        pass

    @abstractmethod
    def live_data(self,urn,api_key):
        pass

    @abstractmethod
    def get_prices(self,api_key):
        pass

    @abstractmethod
    def pred(self,fo):
        pass

class Analyes_News(ABC):
    
    @abstractmethod
    def ProcessNews(self,urls,element,class_element):
        pass

class Data(Model_Data):
    def load_data(self,csv_path):
        global df_final
        df_final = pd.read_csv(csv_path)
   
    def data_preprocessing(self,drop_list):
        # Data pre-processing
        X = df_final.drop(drop_list,axis=1).values
        y = df_final['Action'].values

        # Split Train And Test Data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3)

        # Scale And Standard Variables
        global sc
        sc = StandardScaler()
        X_train = sc.fit_transform(X_train)
        X_test = sc.transform(X_test)

    def load_model(self,path_json,path_h5):
        global loaded_model
        # load json and create model
        json_file = open(path_json, 'r')
        loaded_model_json = json_file.read()
        json_file.close()
        loaded_model = model_from_json(loaded_model_json)
        # load weights into new model
        loaded_model.load_weights(path_h5)
    
    def live_data(self,urn,api_key):
        global price,change,open_price,high_price,low_price

        # get stream live data
        url = urn
        headers = {'x-access-token': api_key}
        resp = requests.get(url, headers=headers)
        resp_dict = resp.json()

        price = resp_dict.get('price')
        price = float(price)
        self.price = price

        change = resp_dict.get('ch')
        change = float(change)
        self.change = change

        open_price = resp_dict.get('open_price')
        open_price = float(open_price)
        self.open_price = open_price

        high_price = resp_dict.get('high_price')
        high_price = float(high_price)
        self.high_price = high_price

        low_price = resp_dict.get('low_price')
        low_price = float(low_price)
        self.low_price = low_price



    def get_prices(self,api_key):
        global prev_open,prev_high,prev_low,prev_close,prev_change,prev_high_low,prev_close_high,prev_sum_4_price,prev_high_plus_low,prev_high_open,prev_open_low
        # load prev prices value
        # read file
        with open('price.json', 'r') as myfile:
            data = myfile.read()

        # parse file
        y = json.loads(data)

        #for all data
        prev_open = y["p_open"]
        prev_high = y["p_high"]
        prev_low = y["p_low"]
        prev_close = y["p_close"]
        prev_change = y["p_change"]
        prev_high_low = prev_high - prev_low
        prev_close_high = prev_close - prev_high
        prev_sum_4_price = prev_open + prev_high + prev_low + prev_close

        #for only data1
        prev_high_plus_low = prev_high + prev_low

        #for only data2
        prev_high_open = prev_high - prev_open

        #for only data3
        prev_open_low = prev_open - prev_low

    def pred(self,fo):
        global pred,buy_counter,sell_counter
        new_pred = loaded_model.predict(sc.transform(np.array([[prev_open,prev_high,prev_low,prev_close,fo,prev_change,prev_high_low,prev_close_high,prev_sum_4_price]])))
        pred = new_pred
        new_pred = (new_pred > 0.5)
        print(pred)

        if (new_pred):
            buy_counter = buy_counter + 1
            print("Buy")
        else:
            sell_counter = sell_counter + 1
            print("Sell")

class News(Analyes_News):
    global s,count_positive,count_neutral,count_negative,urls,pn,sell_counter,pns,percent_negative,percent_positive
    percent_positive = 0
    percent_negative = 0
    pns = NULL


    def ProcessNews(self,urls,element,class_element):
        global pn,pns,stop_words,buy_counter,sell_counter
        stop_words = set(stopwords.words('english'))
        analyzer = SentimentIntensityAnalyzer()

        for url in urls:
            response = requests.get(url)
            soup = BeautifulSoup(response.content, 'html.parser')
            headlines = soup.find_all(element, class_ = class_element)
            for headline in headlines:
                headline = str(headline)

                word_tokens = word_tokenize(headline)
                filtered_sentence = [w for w in word_tokens if not w.lower() in stop_words]
                filtered_sentence = []
                        
                for w in word_tokens:
                    if w not in stop_words:
                        filtered_sentence.append(w)
                        
                    lemma_word = []
                    wordnet_lemmatizer = WordNetLemmatizer()

                    
                    for w in filtered_sentence:
                        word1 = wordnet_lemmatizer.lemmatize(w, pos = "n")
                        word2 = wordnet_lemmatizer.lemmatize(word1, pos = "v")
                        word3 = wordnet_lemmatizer.lemmatize(word2, pos = ("a"))
                        lemma_word.append(word3)
                        

                
                s = filtered_sentence
            
                tweet = s
                tweet = str(tweet)
                tweet = BeautifulSoup(tweet, "lxml").text

                vs = analyzer.polarity_scores(tweet)
                # create TextBlob object of passed tweet text 
                
                import re 
                analysis = TextBlob(' '.join(re.sub("(@[A-Za-z0-9]+)|([^0-9A-Za-z \t])|(\w+:\/\/\S+)", " ", tweet).split())) 
                
                count_negative = 0
                count_positive = 0
                count_neutral = 0

                # set sentiment 
                if(analysis.sentiment.polarity > 0): 
                    count_positive = count_positive + 1
                elif(analysis.sentiment.polarity == 0): 
                    count_neutral = count_neutral + 1
                elif(analysis.sentiment.polarity < 0): 
                    count_negative = count_negative + 1

        try:
            count_all = count_positive + count_negative
            percent_positive = (count_positive * 100 / count_all) - 25
            percent_negative = (count_negative * 100 / count_all) + 25
        except:
            count_all = 0
            percent_positive = 0
            percent_negative = 0

        if(percent_positive >= 50):
            buy_counter = buy_counter + 1
            print("Buy")
            pn = 1
            pns = "Buy"
        elif(percent_negative >= 50):
            sell_counter = sell_counter + 1
            print("Sell")
            pn = -1
            pns = "Sell"
        else:
            print("Neutral")
            pn = 0
            pns = "Neutral"

class Final_Calc:

    def save_signal(self):
        global data_class,final_signal
        data_class = Data()
        print("Buy Counter: ",buy_counter)
        print("Sell Counter: ",sell_counter)
        if(buy_counter > sell_counter):
            final_signal = "Buy"
        elif(sell_counter > buy_counter):
            final_signal = "Sell"
        else:
            final_signal = "Neutral"

        # get day
        today = datetime.now()
        day = today.strftime("%d")

        day = str(day)
        datet = str(today.year)
        datem = str(today.month)
        timeh = str(today.hour)
        timem = str(today.minute)
        # Save in text file

        # Directory
        directory = day+"-"+datem+"-"+datet
        
        # Parent Directory path
        parent_dir = "signal"
        
        # Path
        path = os.path.join(parent_dir, directory)

        if(os.path.isdir(path)): 
            a = 1
        else:
            os.mkdir(path)

        new_path = timeh + "-" + timem + ".txt"
        pred = open("signal/"+directory+"/"+new_path,'w')
        txt = 'Signal: ' + final_signal + '\nBuy: ' + str(buy_counter) + '\nSell: ' + str(sell_counter)
        pred.write(txt)


        print("")
        print("")
        print("")
        print("")
        print("")
        print("")
        print("")
        print("")

        print("      ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓      ")
        print("      ▓                                                                                                              ▓      ")
        print("      ▓                                XAGUSD (Silver Price in US Dollars) Prediction                                  ▓      ")
        print("      ▓                                                                                                              ▓      ")

        print("      ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓      ")

        print("")
        print("        Open	      High	    Low	        Price          Change      	 Buy	        Sell           Final   ")

        print("      ────────────────────────────────────────────────────────────────────────────────────────────────────────────────      ")
        print("     ",open_price,"	    ",high_price," 	 ",low_price,"     ",price,"      ",change,"            ",buy_counter,"              ",sell_counter,"          ",final_signal,"    ")
        print("")
        print("      ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓      ")

        print("")
        print("")
        print("")
        print("")
        print("")
        print("")
        print("")
        print("")      

        # ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
        # ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
        # ---------------------------------------------------------------------------End Code----------------------------------------------------------------------------------
        # ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
        # ---------------------------------------------------------------------------------------------------------------------------------------------------------------------


def pred_silver():
    global silver,silver_news,silver_final,silver_news_1,silver_news_2,silver1,silver2,silver3
    silver = Data()
    silver1 = Data()
    silver2 = Data()
    silver3 = Data()
    silver_news = News()
    silver_news_1 = News()
    silver_news_2 = News()
    silver_final = Final_Calc()

    with open('key') as f:
        api_key = f.read()
    api_key = str(api_key)
    print(api_key)
    
    # get live stream silver data from goldapi.io
    silver.live_data('http://www.goldapi.io/api/XAG/USD',api_key)
    # get silver prices from json file
    silver.get_prices(api_key)

    silver1.load_data('data/1/silver.csv')
    silver1.data_preprocessing(['Date','Action','Change','Open','High','Low','Close'])
    silver1.load_model('model/model-1/model.json','model/model-1/model.h5')
    silver1.pred(prev_high_plus_low)

    silver2.load_data('data/2/silver.csv')
    silver2.data_preprocessing(['Date','Action','Change','Open','High','Low','Close'])
    silver2.load_model('model/model-2/model.json','model/model-2/model.h5')
    silver2.pred(prev_high_open)


    # search in search engine
    # urls 
    urls1 = [
    'https://gerdoo.me/search/?query=xagusd%20twitter%20buy%20sell&page=5&date=day',
    'https://gerdoo.me/search/?query=xagusd%20twitter%20buy%20sell&page=4&date=day',
    'https://gerdoo.me/search/?query=xagusd%20twitter%20buy%20sell&page=3&date=day',
    'https://gerdoo.me/search/?query=xagusd%20twitter%20buy%20sell&page=2&date=day',
    'https://gerdoo.me/search/?query=xagusd%20twitter%20buy%20sell&page=1&date=day',
    'https://gerdoo.me/search/?query=xagusd%20twitter%20analysis&page=5&date=day',
    'https://gerdoo.me/search/?query=xagusd%20twitter%20analysis&page=4&date=day',
    'https://gerdoo.me/search/?query=xagusd%20twitter%20analysis&page=3&date=day',
    'https://gerdoo.me/search/?query=xagusd%20twitter%20analysis&page=2&date=day',
    'https://gerdoo.me/search/?query=xagusd%20twitter%20analysis&page=1&date=day',
    'https://gerdoo.me/search/?query=political%20news&page=5&date=day',
    'https://gerdoo.me/search/?query=political%20news&page=4&date=day',
    'https://gerdoo.me/search/?query=political%20news&page=3&date=day',
    'https://gerdoo.me/search/?query=political%20news&page=2&date=day',
    'https://gerdoo.me/search/?query=political%20news&page=1&date=day',
    'https://gerdoo.me/search/?query=Political%20and%20economic%20news&page=5&date=day',
    'https://gerdoo.me/search/?query=Political%20and%20economic%20news&page=4&date=day',
    'https://gerdoo.me/search/?query=Political%20and%20economic%20news&page=3&date=day',
    'https://gerdoo.me/search/?query=Political%20and%20economic%20news&page=2&date=day',
    'https://gerdoo.me/search/?query=Political%20and%20economic%20news&page=1&date=day',
    ]


    # process news 1
    try:
        silver_news_1.ProcessNews(urls1,'span','highlight-text')
    except:
        pass


    #compire news with data
    silver_final.save_signal()


#Run
pred_silver()

