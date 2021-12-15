import argparse

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.pipeline import Pipeline


def vocabulary(df: pd.DataFrame) -> np.array:
    vectorizer = CountVectorizer()
    _ = vectorizer.fit_transform(df['text'])
    vocab = vectorizer.get_feature_names_out()
    return vocab


def bag_of_words_vector(data: str, vocab: np.array) -> np.array:
    vectorizer = CountVectorizer(vocabulary=vocab)
    X = vectorizer.fit_transform([data])
    return X.toarray()[0]


def tf_idf_vector(data: str, vocab: np.array) -> np.array:
    pipe = Pipeline([('count', CountVectorizer(vocabulary=vocab)), ('tfid', TfidfTransformer())]).fit([data])
    return pipe['tfid'].idf_


def kmeans(data: np.array):
    km = KMeans(n_clusters=2, random_state=0).fit(data)
    return km.labels_


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--in', dest='input_file', default='out.csv', help='input file')
    args = parser.parse_args()

    df = pd.read_csv(args.input_file)
    df.dropna(inplace=True)

    vocab = vocabulary(df)
    df['bow'] = df.apply(lambda x: bag_of_words_vector(x['text'], vocab), axis=1)
    df['tfidf'] = df.apply(lambda x: tf_idf_vector(x['text'], vocab), axis=1)

    bow_clusters = kmeans(np.array(df['bow'].tolist()))
    print(bow_clusters)
    tfidf_clusters = kmeans(np.array(df['tfidf'].tolist()))
    print(tfidf_clusters)


if __name__ == '__main__':
    main()
