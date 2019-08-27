import nltk
from nltk.corpus import stopwords
stop_words = set(stopwords.words('dutch'))
print(len(stop_words))