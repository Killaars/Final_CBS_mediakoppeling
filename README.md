# Final_CBS_mediakoppeling
Repository of the final code for the CBS mediakoppeling assignment.

## Table of contents
1. Introduction
2. Method
3. Results
4. Final model
5. Possible future improvements

## Introduction
The CBS is the leading Dutch statistical institute. They publish their research online [(cbs.nl)](https://www.cbs.nl/ "CBS's Homepage") for the public and news agencies in the Netherlands. These results are often used in news articles or opinion pieces, by politicians, other researchers or the general public, as they are factual and use recent statistics. The CBS wants to know how often their research is used, by which parties, when and in which context. The news articles are manually matched with the CBS research to obtain this knowledge. This project is the first attempt to do this coupling automatically.

## Method
The coupling is based on the theory proposed by the [Fellegi and Sunter model (1969)](https://amstat.tandfonline.com/doi/abs/10.1080/01621459.1969.10501049 "Fellegi and Sunter article"). Each media article ("child" in the code) is coupled to each CBS article ("parent") and their probability of matching is determined based on several characteristics between the articles. These characteristics are:
  * Is the link of the CBS article present in the media article?
  * Is the whole title of the CBS article present in the media article?
  * Do the keywords of the CBS article (given by the researchers) occur in the media article? If so, how much and how much relative to the total number of keywords?
  * And the broader and top term of the keywords? If so, how much and how much relative to the total number of these terms?
  * What about the words of the CBS title (without stopwords?)
  * And the words of the first paragraph of the CBS article without stopwords?
  * Do the numbers of the CBS article match with the numbers of the media article? Numbers are first isolated, standardized and converted to integers (e.g. ten --> 10, 10 thousand --> 10000, 10% --> 10 percent, 10.000 (ten thousand) --> 10000 etc).
  * Is the media article published within two days after the CBS article?
  * The semantic similarity between the titles and the actual content of the media article and CBS article is determined, based on wordvectors of [fasttext](https://fasttext.cc/docs/en/pretrained-vectors.html).
First, a sample of the data from march-april 2019 was used as a train/test set to determine which model type was to be used. This dataset contained 1637 matches and 271944 non-matches. Based on this, a type of model was chosen to be trained and tuned on the full dataset. The final models were trained on a dataset of articles between 01-11-2017 and 24-04-2019. These articles were all manually matched by CBS employees during this period. Of these articles, all matches (86.000) were used, together with a random sample of 414.000 non-matches. The resulting dataset of 500.000 records was split 0.7-0.3 and used as a test/train set. New articles between 25-04-2019 and 14-08-2019 were used for validation of the model. 

## Results
|| Logistic Regression | Naive Bayes | RandomForest | DecisionTree | ADABoost | SVM
--- | --- | --- | --- | --- | --- | --- |
TP | 900 | 1054 | 1265 | 1263 | 1279 | 
FP | 175 | 2055 | 126 | 214 | 136 | 
FN | 737 | 583 | 372 | 726 | 358 | 
TN | 271769 | 269889 | 271818 | 271730 | 271808 | 
Precision | 0.837 | 0.339 | 0.909 | 0.855 | 0.904 | 
Recall | 0.550 | 0.643 | 0.773 | 0.772 | 0.781 | 
Accuracy | 0.997 | 0.990 | 0.998 | 0.998 | 0.998 | 0.997


  
  
  
  ## Possible future improvements
  
  Better word vectors? https://fasttext.cc/docs/en/crawl-vectors.html
