import time
from anoteai import PrivateChatbot

if __name__ == "__main__":
    api_key = '3a414ee04e3efc1bf4cb3b1fc6e5b20b'
    privategpt = PrivateChatbot(api_key)


    file_paths = ['doc1.pdf', 'doc2.pdf']


    print(privategpt.upload(file_paths, 0, 0))

