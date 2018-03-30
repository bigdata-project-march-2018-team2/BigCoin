import sys
import datetime
from datetime import timedelta
from pyspark.sql import SparkSession, Row
from pyspark.ml.feature import CountVectorizer, StringIndexer
from pyspark.ml.classification import NaiveBayes
from pyspark.ml.evaluation import MulticlassClassificationEvaluator
import requests
from elasticsearch import Elasticsearch
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from util_ml import get_next_day, filter_text, get_aggregated_text, format_data

STOPWORDS = set(stopwords.words('english'))
CHAR_TO_REMOVE = ',.:;?!"()'
API_KEYS = 'your API key'
API_KEYS = sys.argv[1]
SPLIT_WEIGHT = 0.6
# default values
es_host = 'localhost' 
es_port = 9200
es_index = 'cours_btc_idx_test'
es_doc_type = 'cours_btc_test'
date_predict = '2018-03-29'
if (len(sys.argv) >= 3):
	date_predict = sys.argv[2]

#Initialize SparkSession
spark = SparkSession \
	.builder \
	.appName("Machine learning Bitcoin") \
	.config("master", "local[3]") \
	.getOrCreate()
sc = spark.sparkContext


def convert(input):
    if isinstance(input, dict):
        return dict((convert(key), convert(value)) for key, value in input.iteritems())
    elif isinstance(input, list):
        return [convert(element) for element in input]
    elif isinstance(input, unicode):
        return input.encode('utf-8')
    else:
        return input
	
def get_next_day(date_str):
	date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
	next_day = date + timedelta(days=1)
	next_date_str = next_day.strftime("%Y-%m-%d")
	return next_date_str
		
def retrieve_bitcoin_cours(date_str):
	es = Elasticsearch([{'host': es_host, 'port': es_port}])
	res = es.get(index=es_index, doc_type=es_doc_type, id=date_str)
	return res

def retrieve_raw_data_day(date_str):
	date_early = date_str+'T00:00:00'
	date_late = date_str+'T23:59:59'
	url_googlenews_api = ('https://newsapi.org/v2/everything?'
       'q=Bitcoin&'
	   'language=en&'
       'from='+date_early+'&'
	   'to='+date_late+'&'
       'sortBy=relevance&'
	   'pageSize=10&'
	   'page=1&'
       'apiKey='+API_KEYS)
	  
	response = requests.get(url_googlenews_api)
	if response.status_code == 200:
		return response.json()
	else:
		# print ('error')
		return None
		# sys.exit(20)

#To do: filter number
def filter_text(text):
	#tokenize text
	list_mots = text.lower().split(' ')
	#filter ponctuations and stopwords
	list_mots = [mot.strip(CHAR_TO_REMOVE) for mot in list_mots]
	list_mots = [mot for mot in list_mots if mot not in STOPWORDS and mot.isalpha()]
	#lemmatize words
	wordnet_lemmatizer = WordNetLemmatizer()
	list_mots = [wordnet_lemmatizer.lemmatize(mot) for mot in list_mots]
	list_mots = [wordnet_lemmatizer.lemmatize(mot, pos='v') for mot in list_mots]
	return list_mots

def get_aggregated_text(formatted_data):
	aggregated_mots = []
	for i in formatted_data:
		date, list_mots = i
		aggregated_mots += list_mots
	return aggregated_mots

def format_data(raw_data):
	formatted_data = []
	for i in range (len(raw_data['articles'])):
		#text_article = (raw_data["articles"][i]["title"])+' '+(raw_data["articles"][i]["description"])
		text_article = (raw_data["articles"][i]["description"])
		if text_article == None:
			return None
		formatted_words_list = filter_text(text_article)
		date_article = (raw_data["articles"][i]["publishedAt"])
		formatted_data.append((date_article, formatted_words_list))
	return formatted_data
	
def extract_features(list_words):
	return vector
	
def prepare_data(rdd):
	rdd = rdd.map(lambda (indice, list): LabeledPoint(indice, extract_features(list)))
	return rdd
	
def split_data(rdd):
	(rdd_train, rdd_test) = rdd.randomSplit([SPLIT_WEIGHT, 1.0 - SPLIT_WEIGHT])
	return (spark.createDataFrame(rdd_train), spark.createDataFrame(rdd_test))
	
def get_data_day(date_str):
	data_search = retrieve_raw_data_day(date_str)
	if data_search != None:
		formatted_data_search = format_data(data_search)
		if formatted_data_search != None:
			data_list_search = get_aggregated_text(formatted_data_search)
			# diff_day = get_variation_value(date_str, get_next_day(date_str))
			# diff_wordslist_search = (diff_day, data_list_search)
			return data_list_search
	return None
	
def predict_result(df):
	# 1.0 bitcoin cours up
	# 0.0 bitcoin cours down
	return 1.0
	
def get_variation_value(date_str, date_next_str):
	date = date_str
	date_suiv = date_next_str
	bitcoin_data_date = (retrieve_bitcoin_cours(date))
	valeur_day = bitcoin_data_date["_source"]["rate"]
	
	bitcoin_data_date = (retrieve_bitcoin_cours(date_suiv))
	valeur_day_next = bitcoin_data_date["_source"]["rate"]
	
	difference = valeur_day_next - valeur_day
	return float(1) if difference >= 0 else float(0)
	
def main():
	date_start = '2018-03-01'
	date_end = '2018-03-27'
	date_search = date_start
	
	tuples_list = []
	while (date_search != date_end):
		# print (date_search)
		'''data_day = retrieve_raw_data_day(date_search)
		if data_day != None:
			formatted_data = format_data(data_day)
			if formatted_data != None:
				data_list = get_aggregated_text(formatted_data)
				#data_list = [mot.encode('utf-8') for mot in data_list]
				# print data_list
				diff = get_variation_value(date_search, get_next_day(date_search))
				diff_wordslist = (diff, data_list)'''
		wordslist = get_data_day(date_search)
		if wordslist != None:
			diff = get_variation_value(date_search, get_next_day(date_search))
			diff_wordslist = (diff, wordslist)
			tuples_list.append(diff_wordslist)
		date_search = get_next_day(date_search)
	
	# print tuples_list
	#rdd to dataframe
	rdd = sc.parallelize(tuples_list)
	rdd = rdd.map(lambda (indice, list): Row(diff=indice, words=list))
	df_train, df_test = split_data(rdd)
	#df_data = spark.createDataFrame(rdd)
	
	# Vectorizer : extract features from list of words
	# Estimator type CountVectorizer
	count_vectorizer = CountVectorizer(inputCol='words', outputCol='features')
	vectorizer_transformer = count_vectorizer.fit(df_train)
	
	# Apply Transformer
	train_bag_of_words = vectorizer_transformer.transform(df_train)
	test_bag_of_words = vectorizer_transformer.transform(df_test)
	
	# Indexer : extract label from difference in value from two days
	# Indexer for indexing difference value, up or down (constant ?)
	label_indexer = StringIndexer(inputCol='diff', outputCol='label_index')
	label_indexer_transformer = label_indexer.fit(train_bag_of_words)
	
	# Apply transformer
	train_bag_of_words = label_indexer_transformer.transform(train_bag_of_words)
	test_bag_of_words = label_indexer_transformer.transform(test_bag_of_words)
	
	# Classifier type : NaiveBayes
	# Train
	classifier = NaiveBayes(labelCol='label_index', featuresCol='features', predictionCol='label_predicted')
	classifier_transformer = classifier.fit(train_bag_of_words)
	# Apply classifier trained on test data
	# Test
	test_predicted = classifier_transformer.transform(test_bag_of_words)
	# Evaluator
	# Evaluation
	evaluator = MulticlassClassificationEvaluator(labelCol='label_index', predictionCol='label_predicted', metricName='accuracy')
	accuracy = evaluator.evaluate(test_predicted)
	
	print ('Accuracy : '+ str(accuracy*100)+'%')
	
	# Predict specific day
	date_predict = '2018-03-26'
	wordlist_predict = get_data_day(date_predict)
	tuple = (0.0, wordlist_predict)
	table = []
	table.append(tuple)
	
	rdd_predict = sc.parallelize(table)
	rdd_predict = rdd_predict.map(lambda (indice, list): Row(diff=indice, words=list))
	df_predict = spark.createDataFrame(rdd_predict)
	
	df_predict_vect = vectorizer_transformer.transform(df_predict)
	df_predict = label_indexer_transformer.transform(df_predict_vect)
	df_predicted = classifier_transformer.transform(df_predict)
	
	print ('Resultat prediction pour le jour '+date_search)
	df_predicted.show()
	

if __name__ == "__main__":
	main()
