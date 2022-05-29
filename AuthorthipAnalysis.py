# Import required libraries, etc.
import sys
import os
import collections
import random
import re
import math
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
    each_word_occurrence_rate_by_author = dict()

    ngram_numbers = [1, 2, 3]

    def __init__(self, client, user_name_1, user_name_2):
        self.client = client
        self.user_name_1 = user_name_1
        self.user_name_2 = user_name_2

        self.create_tweet_texts_by_author()

        self.divide_questioned_texts_and_known_texts()

        self.create_ngram_count_by_author()

        self.create_each_word_occurrence_rate_by_author()

    def create_tweet_texts_by_author(self):
        for user_name in [self.user_name_1, self.user_name_2]:
            user_id = self.client.get_user(username = user_name).data.id

            pagination_token = None
            for i in range(100):
                tweets = self.client.get_users_tweets(id = user_id,
                                                 max_results = 100,
                                                 exclude = "retweets",
                                                 pagination_token = pagination_token)

                for tweet_data in tweets.data:
                    remove_url_text = re.sub(r"\S*https?:\S*", "", tweet_data["text"])
                    self.tweet_texts_by_author[user_name].append(remove_url_text)

                try:
                    pagination_token = tweets.meta["next_token"]
                except KeyError:
                    break

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
        for user_name in [self.user_name_1, self.user_name_2]:
            self.ngram_count_by_author[user_name] = dict()

            for n in self.ngram_numbers:
                self.ngram_count_by_author[user_name][n] = collections.defaultdict(lambda: int())

                for known_text in self.known_texts_by_author[user_name]:
                    tokenized_text = get_tokenized_text(known_text)
                    for ngram in nltk.ngrams(tokenized_text, n):
                        self.ngram_count_by_author[user_name][n][ngram] += 1

    def create_each_word_occurrence_rate_by_author(self):
        for user_name in [self.user_name_1, self.user_name_2]:
            self.each_word_occurrence_rate_by_author[user_name] = collections.defaultdict(lambda: float())

            word_count_sum = sum(self.ngram_count_by_author[user_name][1].values())

            for word, word_count in self.ngram_count_by_author[user_name][1].items():
                word_occurrence = word_count / word_count_sum
                self.each_word_occurrence_rate_by_author[user_name][word] = word_occurrence

    def analysis(self):
        total_questioned_text_cnt = sum(len(questioned_texts) for questioned_texts in self.questioned_texts_by_author.values())
        correct_author_cnt = 0

        for question_user_name in [self.user_name_1, self.user_name_2]:
            for questioned_text in self.questioned_texts_by_author[question_user_name]:
                score_dict = collections.defaultdict(lambda: int())
                tokenized_text = get_tokenized_text(questioned_text)
                for n in self.ngram_numbers:
                    for ngram in nltk.ngrams(tokenized_text, n):
                        for known_user_name in [self.user_name_1, self.user_name_2]:
                            score_dict[known_user_name] += self.ngram_count_by_author[known_user_name][n][ngram] * math.pow(50, n - 1)

                user_1_word_count = sum(self.ngram_count_by_author[self.user_name_1][1].values())
                user_2_word_count = sum(self.ngram_count_by_author[self.user_name_2][1].values())

                ratio = user_1_word_count / user_2_word_count
                score_dict[self.user_name_1] /= ratio

                for known_user_name in [self.user_name_1, self.user_name_2]:
                    for word in nltk.ngrams(tokenized_text, 1):
                        score_dict[known_user_name] += self.each_word_occurrence_rate_by_author[known_user_name][word] * 100000

                result_user_name = str()
                max_score = 0
                for user_name, score in score_dict.items():
                    if score > max_score:
                        max_score = score
                        result_user_name = user_name

                if question_user_name == result_user_name:
                    correct_author_cnt += 1

        print(f'{correct_author_cnt} of {total_questioned_text_cnt} questioned texts were correctly determined.')


# Main process of the program
def main(args):

    if len(args) != 3:
        print("Please enter two Twitter usernames.")
        exit()

    user_name_1 = args[1]
    user_name_2 = args[2]

    print(f'author 1: @{user_name_1}')
    print(f'author 2: @{user_name_2}')

    print()

    client = setup_twitter_api()

    print("Creating verifier...")
    print()

    authorshipVerifier = AuthorshipVerifier(client, user_name_1, user_name_2)

    print("Analyzing...")
    print()

    authorshipVerifier.analysis()


main(sys.argv)
