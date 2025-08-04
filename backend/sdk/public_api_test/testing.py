import time
from anoteai import PrivateChatbot

if __name__ == "__main__":
    api_key = '085532bd27b51787f0ab39e786811046'
    privategpt = PrivateChatbot(api_key)


    file_paths = ['doc1.pdf', 'doc2.pdf']


    print(privategpt.upload(file_paths, 0, 0))

