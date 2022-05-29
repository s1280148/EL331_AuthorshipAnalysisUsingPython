# Import required libraries, etc.
import sys
import os
import collections
import random
import re
from dotenv import load_dotenv
import tweepy
import nltk


###
# This function prepares to use the Twitter API.
# Use "tweepy" to simplify the use of the API.
# Environment variables must be defined in the ".env" file.
###
def setup_twitter_api():
    load_dotenv()

    API_KEY = os.environ.get("API_KEY")
    API_KEY_SECRET = os.environ.get("API_KEY_SECRET")
    BEARER_TOKEN = os.environ.get("BEARER_TOKEN")
    ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")
    ACCESS_TOKEN_SECRET = os.environ.get("ACCESS_TOKEN_SECRET")

    client = tweepy.Client(consumer_key = API_KEY,
                           consumer_secret = API_KEY_SECRET,
                           bearer_token = BEARER_TOKEN,
                           access_token = ACCESS_TOKEN,
                           access_token_secret = ACCESS_TOKEN_SECRET)

    return client


def get_tokenized_text(original_text):
    tokenizer = nltk.tokenize.RegexpTokenizer(r'\w+')
    return tokenizer.tokenize(original_text)

###
# This class performs Authorship Verification.
###
class AuthorshipVerifier:

    client = None
    user_name_1 = str()
    user_name_2 = str()
    tweet_texts_by_author = collections.defaultdict(lambda: list())
    known_texts_by_author = dict()
    questioned_texts_by_author = dict()
    ngram_count_by_author = dict()

    def __init__(self, client, user_name_1, user_name_2):
        self.client = client
        self.user_name_1 = user_name_1
        self.user_name_2 = user_name_2

        self.create_tweet_texts_by_author()

        self.divide_questioned_texts_and_known_texts()

        self.create_ngram_count_by_author()

    def create_tweet_texts_by_author(self):
        for user_name in [self.user_name_1, self.user_name_2]:
            user_id = self.client.get_user(username = user_name).data.id

            pagination_token = None
            for i in range(20):
                tweets = self.client.get_users_tweets(id = user_id,
                                                 max_results = 100,
                                                 exclude = "retweets",
                                                 pagination_token = pagination_token)

                for tweet_data in tweets.data:
                    remove_url_text = re.sub(r"\S*https?:\S*", "", tweet_data["text"])
                    self.tweet_texts_by_author[user_name].append(remove_url_text)

                pagination_token = tweets.meta["next_token"]

    def divide_questioned_texts_and_known_texts(self):
        for user_name in [self.user_name_1, self.user_name_2]:
            tweet_texts = self.tweet_texts_by_author[user_name]
            shuffled_tweet_texts = random.sample(tweet_texts, len(tweet_texts))

            known_text_count = int(len(shuffled_tweet_texts) * 0.9)

            known_texts = shuffled_tweet_texts[:known_text_count]
            questioned_texts = shuffled_tweet_texts[known_text_count:]

            self.known_texts_by_author[user_name] = known_texts
            self.questioned_texts_by_author[user_name] = questioned_texts

    def create_ngram_count_by_author(self):
        ngram_numbers = [1, 2, 3]
        for user_name in [self.user_name_1, self.user_name_2]:
            self.ngram_count_by_author[user_name] = dict()

            for n in ngram_numbers:
                self.ngram_count_by_author[user_name][n] = collections.defaultdict(lambda: int())

                for known_text in self.known_texts_by_author[user_name]:
                    tokenized_text = get_tokenized_text(known_text)
                    for ngram in nltk.ngrams(tokenized_text, n):
                        self.ngram_count_by_author[user_name][n][ngram] += 1


# Main process of the program
def main(args):

    if len(args) != 3:
        print("Please enter two Twitter usernames.")
        exit()

    user_name_1 = args[1]
    user_name_2 = args[2]

    client = setup_twitter_api()

    authorshipVerifier = AuthorshipVerifier(client, user_name_1, user_name_2)


main(sys.argv)
