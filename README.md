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
First, a sample of the data from march-april 2019 was used as a train/test set to determine which model type was to be used. This dataset contained 1637 matches and 271944 non-matches. Based on this, a type of model was chosen to be trained and tuned on the full dataset. The final models were trained on a dataset of articles between 01-11-2017 and 24-04-2019. These articles were all manually matched by CBS employees during this period. Of these articles, all matches (86.000) were used, together with a random sample of 414.000 non-matches. The resulting dataset of 500.000 records was split 0.7-0.3 and used as a test/train set. New articles between 25-04-2019 and 14-08-2019 were used for validation of the model. This validation set contained 3045 matches and 3917955 non-matches, a ratio more similar to the ratio when the model would be used in production. 

## Results
The first dataset was used to select the model type to use with the full dataset. A subset was chosen to save computation time and to allow for a gridsearch to find good hyperparameters for each model type. Based on these results (see table 1), the tree type models (RandomForest, DecisionTree and ADABoost) performed best. Even though an ADABoost model performed best, the RandomForest model was chosen for the next stage due to the comparable results with a much faster training and prediction. 

##### Table 1 - Results on first dataset for different models. Each model was trained with a gridsearch on a wide range of parameters. 
|| Logistic Regression | Naive Bayes | RandomForest | DecisionTree | ADABoost | SVM
--- | --- | --- | --- | --- | --- | --- |
True Positive (TP) | 900 | 1054 | 1265 | 1263 | 1279 | 
False Positive (FP) | 175 | 2055 | 126 | 214 | 136 | 
False Negative (FN) | 737 | 583 | 372 | 726 | 358 | 
True Negative (TN) | 271769 | 269889 | 271818 | 271730 | 271808 | 
Precision | 0.837 | 0.339 | 0.909 | 0.855 | 0.904 | 
Recall | 0.550 | 0.643 | 0.773 | 0.772 | 0.781 | 
Accuracy | 0.997 | 0.990 | 0.998 | 0.998 | 0.998 | 0.997

After a RandomSearch and a Gridsearch on a wide range of hyperparameter settings, the best setup for the RandomForest obtained a precision of 97.1% and a recall of 95.1% (table 2). The forest contained 150 trees, with a depth of 40 layers, no bootstrapping and a minimum sample split of 2. However, we found that this model was greatly overfitting the trainingsset and performed very poorly when using this model for the validation set. It found more than 1 million FPs with high certainty, meaning that more than a quarter of all possible matches were found. 2806 (92%) of all matched were found as well, but that is completely worthless when you also have an overload of FP's. Even though we could not pinpoint the exact cause of this, we expect some temporal discrepancy between the validation and testset to be the cause. However, we could not really account for this, as the model will also be used on new data, with possible temporal differences as well. The model had to become more robust and less prone to overfitting and was therefore pruned significantly. We found that reducing the depth of the trees to 4 (instead of 40) and only allowing leaves with at least 20 samples improved the model. The number of FP's dropped to almost 38000, but the accuracy of the FP's dropped well below the accuracy of the TP's. The highest matchingsprobability for 1925 children was the actual match and for 274 was the actual match in the top 5. 


|| Unpruned model | Pruned model
--- | --- | ---
**Trainingsset** | | 
TP | 24180 | 22151
FP | 730 | 1240
FN | 1525 | 3073
TN | 122705 | 116400
Precision | 0.970 | 0.947
Recall | 0.940 | 0.878
 | | 
**Validationset** | | 
TP | 2806 | 2416
FP | 1116330 | 37696
FN | 239 | 498
TN | 2801625 | 3868390
Precision | 0.0025 | 0.060
Recall | 0.922 | 0.829
 | | 
**Model setup**
Nr of Trees | 150 | 150
Depth | 40 | 4
Minimum samples per leaf | 1 | 20



  
  
  
  ## Possible future improvements
  
  Better word vectors? https://fasttext.cc/docs/en/crawl-vectors.html
