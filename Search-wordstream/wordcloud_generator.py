from wordcloud import WordCloud
from sklearn.feature_extraction.text import TfidfVectorizer
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import io
import pandas as pd

def generate_word_cloud(contents):
    # Calculate TF-IDF scores for the contents
    tfidf_vectorizer = TfidfVectorizer()  # You can pass stopwords and other options as needed
    tfidf_matrix = tfidf_vectorizer.fit_transform(contents)

    # Get the feature names (words) and their corresponding TF-IDF scores
    feature_names = tfidf_vectorizer.get_feature_names_out()
    tfidf_scores = tfidf_matrix.sum(axis=0).A1

    # Create a dictionary to store words and their TF-IDF scores
    word_tfidf_dict = dict(zip(feature_names, tfidf_scores))

    # Create a WordCloud based on TF-IDF scores
    wordcloud = WordCloud(
        background_color='white',
        max_words=60,
        width=800,
        height=400,
        collocations=False
    ).generate_from_frequencies(word_tfidf_dict)

    # Calculate word frequencies for the bar chart
    text = ' '.join(contents)
    word_freq = pd.Series(text.split()).value_counts()[:20]

    # Set up the figure and use GridSpec for custom layout
    fig = plt.figure(figsize=(8, 10))  # Adjusted figsize for vertical layout
    gs = gridspec.GridSpec(2, 1)  # 2 rows, 1 column

    ax1 = plt.subplot(gs[0])  # Word cloud on the top
    ax2 = plt.subplot(gs[1])  # Bar chart at the bottom

    # Plot the word cloud on the first axis
    ax1.imshow(wordcloud, interpolation="bilinear")
    ax1.axis("off")
    ax1.set_title("Word Cloud")

    # Plot the word frequencies on the second axis
    word_freq.plot(kind='bar', color='skyblue', ax=ax2)
    ax2.set_title('Word Frequency of Most Common Words')
    ax2.set_ylabel('Frequency')
    ax2.set_xlabel('Words')
    ax2.set_xticklabels(word_freq.index, rotation=90, fontsize=10)  # Adjust fontsize if needed

    # Save the combined figure to a BytesIO object
    img = io.BytesIO()
    plt.tight_layout(pad=2)
    plt.savefig(img, format="png")
    img.seek(0)

    return img