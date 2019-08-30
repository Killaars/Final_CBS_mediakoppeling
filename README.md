# Final_CBS_mediakoppeling
Repository of the final code for the CBS mediakoppeling assignment.

## Table of contents
0. Requirements
1. Introduction
2. Method
3. Results
4. Possible future improvements
5. Other scripts

## Requirements
* python                             3.7.3
* pandas                             0.24.2
* recordlinkage                      0.13.2
* scikit-learn                       0.21.2
* spacy                              2.1.6

## Introduction
The CBS is the leading Dutch statistical institute. They publish their research online [(cbs.nl)](https://www.cbs.nl/ "CBS's Homepage") for the public and the news agencies in the Netherlands. Their results are often used in news articles or opinion pieces, by politicians, other researchers or the general public, as they are factual and use recent statistics. The CBS wants to know when and how often their research is used, by which parties and in which context. The news articles are manually matched with the CBS research articles to obtain this knowledge. This project is the first attempt to do this coupling automatically.

## Method

The coupling method is based on classifying all candidate pairs into matches and non-matches, somewhat similar to the
method proposed by [Fellegi and Sunter (1969)](https://amstat.tandfonline.com/doi/abs/10.1080/01621459.1969.10501049 "Fellegi and Sunter article"). Here, each media article (or "child") is paired with each CBS article ("parent") and their probability of matching is derived from several characteristics between the articles. These characteristics are:
  * Do the keywords of the CBS article (given by the researchers) occur in the media article? If so, how much and how much relative to the total number of keywords?
  * For each key word, CBS has strongly related concepts (top terms) and weaker related concepts (broader terms). Occurrence and relative count are incorporated as well.
  * Similar for words of the CBS title (without stopwords?)
  * Similar for words of the first paragraph of the CBS article without stopwords.
  * Do the numbers of the CBS article match with the numbers of the media article? Numbers are first isolated, standardized and converted to integers (e.g. ten --> 10, 10 thousand --> 10000, 10% --> 10 percent, 10.000 (ten thousand) --> 10000, half a million --> 500000 etc.).
  Both how much of the features above are found in the child article and how much they could have been found are used in the match prediction. Apart from this, the following characteristics also play a role:
  * Is the link of the CBS article present in the media article?
  * Is the whole title of the CBS article present in the media article?
  * Is the media article published within two days after the CBS article?
  * The semantic similarity between the titles and the actual content of the media article and CBS article is determined, based on wordvectors of [fasttext](https://fasttext.cc/docs/en/pretrained-vectors.html).
After the features of the possible matches were found, a sample of the data from march-april 2019 was used as a train/test set to determine which model type was to be used. This dataset contained 1637 matches and 271944 non-matches. Based on this, a type of model was chosen to be trained and tuned on the full dataset. The final models were trained on a dataset of articles between 01-11-2017 and 24-04-2019. These articles were all manually matched by CBS employees during this period. Of these articles, all matches (86.000) were used, together with a random sample of 414.000 non-matches. The resulting dataset of 500.000 records was split 0.7-0.3 and used as a test/train set. New articles between 25-04-2019 and 14-08-2019 were used for validation of the model. This validation set contained 3045 matches and 3917955 non-matches, a ratio more similar to the actual ratio when the model would be used in production. 

## Results
The small dataset of two months was used to select the model type to use with the full dataset. A subset was chosen to save computation time and to allow for a gridsearch to find good hyperparameters for each model type. Based on these results (see table 1), the tree type models (RandomForest, DecisionTree and ADABoost) performed best. Even though an ADABoost model performed better, the RandomForest model was chosen for the next stage due to the comparable results with a much faster training and prediction. 

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

After a RandomSearch and a Gridsearch on a wide range of hyperparameter settings, the best setup for the RandomForest resulted in a precision of 97.1% and a recall of 95.1% (table 2). The forest contained 150 trees, a depth of 40 layers, no bootstrapping and a minimum sample split of 2 samples in a leaf. However, we found that this model was greatly overfitting the trainingsset and performed very poorly when it was used for the validation set. It found more than 1 million FPs with high certainty, meaning that more than a quarter of all possible matches were found. 2806 (92%) of all matched were found as well, but that is completely worthless when you also have an overload of FP's. Even though we could not pinpoint the exact cause of this, we expect some temporal discrepancy between the validation and testset to be the cause. However, we could not really account for this by changing the datasets, as the model will also be used on new data during production, with possible temporal differences as well. The model had to become more robust and less prone to overfitting and was therefore pruned severely. We found that reducing the depth of the trees to 4 (instead of 40) and only allowing leaves with at least 20 samples improved the model. The number of FP's in the validation set dropped to almost 38000, but the accuracy of the FP's dropped well below the accuracy of the TP's. The parent with the highest matchings probability for 1925 children was the actual match and the actual match was in the top 5 for 274 other children. Moreover, the amount of FP's drops to 414 when only the highest matchings probability is taken into account. The fact that the model is more uncertain about the FP's than the TP's becomes clear in Figure 1 and can be used for further differentiation. The figure shows that the amount of FP's is reduced faster than the amount of TP's when the probability cut-off is increased. For example, when only matches with a probability higher than 0.9 are taken into account, only 47 FP's remain, versus 1388 TP's. This relationship can be used to determine a threshold value for automatic matching of the articles and can be tweaked to obtain more reliability or more automatic matches. 

##### Table 2
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

##### Figure 1: Number of TP's and FP's for different probabilities. 
![alt text](https://github.com/Killaars/Final_CBS_mediakoppeling/blob/master/TPandFPvs_probabilityplot.png "probability_plot")

 
  ## Possible future improvements
  Given the limited time span for this project and the fact that all features and the model had to be build from scratch, there remain several possible improvements that were not, or only very briefly, explored. These are described below to provide a starting point for any future work:
  * Which words are found? Probably the biggest improvement can be gained if the model would take the quality of the keywords that are found into account. It only uses 'if' keywords are found and 'how much'. The jaccard scores that play a large role in the final probability consist of the number of keywords that occur in the child article, divided by the total number of possible keywords of the parent. If 3 out of 4 keywords are found, the score becomes 0.75 while 1 out 1 returns a score of 1, even though the former match might be stronger. This is partly accounted for in the 'len_matches' variable, but could be improved.
  * Better word vectors. The model used word vectors determined by fasttext from the Dutch Wikipedia. However, more relevant vectors for CBS articles and news sites might improve the reliability of these vectors. Due to time constraints this is not done.
  * Predicting the CBS themes and using this as a feature. It might be possible to determine the CBS themes related to the children articles and use this as a feature to determine the parent article. If the predicted theme and the parent theme correspond, the match probability should be higher than if they do not correspond. This was explored briefly in [this repository](https://github.com/Killaars/CBS-themes) and showed some promise, but was not included or explored further.
  * The media source of the 'child' article.
  
  ## Other scripts
  This repository only contains the final scripts for this project. More, but relatively unfinished/undocumented, scripts can be found at [the working repository](https://github.com/Killaars/CBS2_mediakoppeling).
