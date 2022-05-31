# Import required modules.
import sys
import os
import collections
import random
import re
import math
from dotenv import load_dotenv
import tweepy
import nltk


def setup_twitter_api():
    """ Prepare to use Twitter's API.

    The information required to use the API must be in the ".env" file.
    To simplify the use of the API, use the "tweepy" module.
    For more information on "tweepy", see https://docs.tweepy.org/en/stable/

    Returns:
        tweepy.Client: Twitter API v2 Client.
    """
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
    """ Get a list of word tokens.

    Retrieves only word tokens from the original text and returns them as a list. (Punctuation is excluded.)
    The Natural Language Toolkit (nltk) module is used to retrieve tokenized text.
    For more information on "nltk", see https://www.nltk.org/

    Args:
        original_text (str): Text to be tokenized.
    Returns:
        list[str]: List of word tokens.
    """
    tokenizer = nltk.tokenize.RegexpTokenizer(r'\w+')
    return tokenizer.tokenize(original_text)


class AuthorshipVerifier:
    """ Authorship Verifier

    This class performs authorship verification.
    It receives two twitter usernames and tweepy.Client, then detects features from the tweets.
    Invoking analysis() will analyze and output the results.

    Attributes:
        client (tweepy.Client): Twitter API v2 Client.
        author_names (list[str]): List of names of two authors.
        tweet_texts_by_author (dict[str, list[str]]): Dictionary containing the text of each author's tweets.
        known_texts_by_author (dict[str, list[str]]): Dictionary containing known text of each author's tweets.
        questioned_texts_by_author (dict[str, list[str]]): Dictionary containing questioned text of each author's tweets.
        ngram_count_by_author (dict[str, dict[int, dict[tuple(str, str, ...), int]]]): Dictionary of the number of occurrences of n-grams in each author's text.
        each_word_occurrence_rate_by_author (dict[str, dict[tuple(str), float]]): Dictionary recording the rate of occurrence of each word for each author.
        questioned_texts_analysis_result (list[tuple(str, str, bool)]): List of tuple that stores the author, text, and whether the result of questioned text analysis is correct or not.
        known_texts_for_compare_questioned_texts (list[tuple(str, str)]): List of tuple containing the authors and sentences of randomly selected known text to be compared with the questioned text.
        ngram_numbers (list[int]): List of n of the n-gram to be created.
    """
    client = None
    author_names = list()
    tweet_texts_by_author = collections.defaultdict(lambda: list())
    known_texts_by_author = dict()
    questioned_texts_by_author = dict()
    ngram_count_by_author = dict()
    each_word_occurrence_rate_by_author = dict()
    questioned_texts_analysis_result = list()
    known_texts_for_compare_questioned_texts = list()

    ngram_numbers = [1, 2, 3]

    def __init__(self, client, user_name_1, user_name_2):
        """ Constructor.

        Collect tweets from each author and create data on characteristics.

        Args:
            client (tweepy.Client): Twitter API v2 Client.
            user_name_1 (str): First author's Twitter username.
            user_name_2 (str): Second author's Twitter username.
        """

        self.client = client
        self.author_names = [user_name_1, user_name_2]

        self.create_tweet_texts_by_author()

        self.divide_questioned_texts_and_known_texts()

        self.create_ngram_count_by_author()

        self.create_each_word_occurrence_rate_by_author()

    def create_tweet_texts_by_author(self):
        """ Create dictionary containing the text of each author's tweets.

        Brief description of the structure of tweet_texts_by_author:
            tweet_texts_by_author[author_name] = List of author's tweet text.
        """
        for author_name in self.author_names:
            user_id = self.client.get_user(username = author_name).data.id

            # Only a maximum of 100 tweets can be retrieved in a 1-time API call.
            # Pagination tokens can be used to achieve the first 1 to 100 tweets and the next 101 to 200 tweets.
            pagination_token = None
            for i in range(20):
                tweets = self.client.get_users_tweets(id = user_id,
                                                 max_results = 100,
                                                 exclude = "retweets",
                                                 pagination_token = pagination_token)

                for tweet_data in tweets.data:
                    # Remove URL from text using regular expressions.
                    remove_url_text = re.sub(r"\S*https?:\S*", "", tweet_data["text"])
                    self.tweet_texts_by_author[author_name].append(remove_url_text)

                try:
                    pagination_token = tweets.meta["next_token"]
                except KeyError:
                    break

    def divide_questioned_texts_and_known_texts(self):
        """ Create a dictionary by dividing the author's text into known text and questioned text, respectively.

        90% of each author's text will be known text and 10% will be questioned text.
        Which text will be known text and which text will be questioned_text will be randomly determined.

        Brief description of the structure of known_texts_by_author and questioned_texts_by_author:
            known_texts_by_author[author_name] = List of author's known text.
            questioned_texts_by_author[author_name] = List of author's questioned text.
        """
        for author_name in self.author_names:
            tweet_texts = self.tweet_texts_by_author[author_name]
            shuffled_tweet_texts = random.sample(tweet_texts, len(tweet_texts))

            known_text_count = int(len(shuffled_tweet_texts) * 0.9)

            known_texts = shuffled_tweet_texts[:known_text_count]
            questioned_texts = shuffled_tweet_texts[known_text_count:]

            self.known_texts_by_author[author_name] = known_texts
            self.questioned_texts_by_author[author_name] = questioned_texts

    def create_ngram_count_by_author(self):
        """ Create dictionary of the number of occurrences of n-grams in each author's text.

        The Natural Language Toolkit (nltk) module is used to create n-gram.
        For more information on "nltk", see https://www.nltk.org/

        Brief description of the structure of ngram_count_by_author:
            ngram_count_by_author[author_name] = Dictionary of n and corresponding n-grams.
            ngram_count_by_author[author_name][n] = Dictionary containing n-grams and their number of occurrences.
            ngram_count_by_author[author_name][n][n-gram] = Number of occurrences of the specified n-gram.

            Example:
                ngram_count_by_author["Johnson"][2][("an", "apple")] = The number of occurrences of "an apple" in Jonson sentences can be obtained. (bi-gram)
        """
        for author_name in self.author_names:
            self.ngram_count_by_author[author_name] = dict()

            for n in self.ngram_numbers:
                self.ngram_count_by_author[author_name][n] = collections.defaultdict(lambda: int())

                for known_text in self.known_texts_by_author[author_name]:
                    tokenized_text = get_tokenized_text(known_text)
                    for ngram in nltk.ngrams(tokenized_text, n):
                        self.ngram_count_by_author[author_name][n][ngram] += 1

    def create_each_word_occurrence_rate_by_author(self):
        """ Create dictionary of recording the rate of occurrence of each word for each author.

        Brief description of the structure of each_word_occurrence_rate_by_author:
            each_word_occurrence_rate_by_author[author_name] = Dictionary of word to word occurrence rates.
            each_word_occurrence_rate_by_author[author_name][word] = Word occurrence rate.

            Example:
                each_word_occurrence_rate_by_author["Johnson"][("apple")] = Occurrence rate of "apple" in Johnson's texts can be retrieved.
          """
        for author_name in self.author_names:
            self.each_word_occurrence_rate_by_author[author_name] = collections.defaultdict(lambda: float())

            word_count_sum = sum(self.ngram_count_by_author[author_name][1].values())

            for word, word_count in self.ngram_count_by_author[author_name][1].items():
                word_occurrence = word_count / word_count_sum
                self.each_word_occurrence_rate_by_author[author_name][word] = word_occurrence

    def analysis(self):
        """ Perform the analysis phase.

        Perform analysis and display analysis results.
        """
        self.create_questioned_texts_analysis_result()

        self.create_known_texts_for_compare_questioned_texts()

        self.compare_author_of_questioned_text_and_known_text()

        self.print_accuracy()

    def create_questioned_texts_analysis_result(self):
        """ Create list of tuple that stores the author, text, and whether the result of questioned text analysis is correct or not.

        Predicts who the author of each questioned text is using the characteristics of each author learned from the known texts.
        Using the characteristics of each author, we score the matches and determine that the text is by the author with the higher score.

        Score Summary:
            uni-gram match: 1 * Number of its uni-grams.
            bi-gram match:  50 * Number of its bi-grams.
            tri-gram match: 2500 * Number of its tri-grams.
            Word appears:   100000 * Occurrence rate of the word.
        """
        for question_author_name in self.author_names:
            for questioned_text in self.questioned_texts_by_author[question_author_name]:
                score_dict = collections.defaultdict(lambda: int())
                tokenized_text = get_tokenized_text(questioned_text)
                for n in self.ngram_numbers:
                    for ngram in nltk.ngrams(tokenized_text, n):
                        for known_author_name in self.author_names:
                            score_dict[known_author_name] += self.ngram_count_by_author[known_author_name][n][ngram] * math.pow(50, n - 1)

                # Scores are adjusted by word count to avoid extreme differences depending on the total number of words in the author's text.
                author_1_total_word_count = sum(self.ngram_count_by_author[self.author_names[0]][1].values())
                author_2_total_word_count = sum(self.ngram_count_by_author[self.author_names[1]][1].values())

                total_word_count_ratio = author_1_total_word_count / author_2_total_word_count
                score_dict[self.author_names[0]] /= total_word_count_ratio

                for known_author_name in self.author_names:
                    for word in nltk.ngrams(tokenized_text, 1):
                        score_dict[known_author_name] += self.each_word_occurrence_rate_by_author[known_author_name][word] * 100000

                result_author_name = max(score_dict.items(), key = lambda score_info: score_info[1])[0]

                is_collect_author = result_author_name == question_author_name

                questioned_text_analysis_result = (result_author_name, questioned_text, is_collect_author)

                self.questioned_texts_analysis_result.append(questioned_text_analysis_result)

    def create_known_texts_for_compare_questioned_texts(self):
        """ Create list of tuple containing the authors and sentences of randomly selected known text to be compared with the questioned text.

        Known text is randomly selected regardless of the author.
        """
        known_texts_info = list()

        for author_name in self.author_names:
            for known_text in self.known_texts_by_author[author_name]:
                known_texts_info.append((author_name, known_text))

        total_questioned_text_cnt = sum(len(questioned_texts) for questioned_texts in self.questioned_texts_by_author.values())

        self.known_texts_for_compare_questioned_texts = random.sample(known_texts_info, total_questioned_text_cnt)

    def compare_author_of_questioned_text_and_known_text(self):
        """ Compare the authors of known text and questioned text.

        It displays each text and its results, showing how many were by the same author at the end.
        """
        total_questioned_text_cnt = sum(len(questioned_texts) for questioned_texts in self.questioned_texts_by_author.values())
        same_author_count = 0

        print(f'There are {total_questioned_text_cnt} questioned text.')

        print()

        for i in range(total_questioned_text_cnt):
            known_text_info = self.known_texts_for_compare_questioned_texts[i]
            questioned_text_info = self.questioned_texts_analysis_result[i]

            pre_line = f'{i + 1})' + '-' * 500
            post_line = '-' * len(pre_line)

            print(pre_line)

            print("・Known text")
            print(known_text_info[1])

            print()

            print("・Questioned text")
            print(questioned_text_info[1])

            print()

            print("・Result")
            if known_text_info[0] == questioned_text_info[0]:
                print("Same author.")
                same_author_count += 1
            else:
                print("Different author.")

            print(post_line)

            print()

        print(f"{same_author_count} of {total_questioned_text_cnt} text is same author.")

        print()

    def print_accuracy(self):
        """ Displays the accuracy of the authorship verification.
        """
        total_questioned_text_cnt = sum(len(questioned_texts) for questioned_texts in self.questioned_texts_by_author.values())
        correct_author_cnt = len(list(filter(lambda question_text_info: question_text_info[2] is True, self.questioned_texts_analysis_result)))

        print(f"Accuracy: {correct_author_cnt / total_questioned_text_cnt * 100} %")


def main(args):
    """ Execute the main process.

    Step 1: Prepare to use Twitter's API.
    Step 2: Get two twitter usernames from command line arguments.
    Step 3: Create an Authorship Verifier.
    Step 4: Invoke analysis() of the authorship verifier.

    Args:
        args (list[str]): List of command line arguments.
    """

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

    authorshipVerifier.analysis()


# Execute the main process.
main(sys.argv)
