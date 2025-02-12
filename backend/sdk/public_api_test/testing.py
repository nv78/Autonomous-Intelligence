import time
from anoteai import PrivateChatbot

if __name__ == "__main__":
    api_key = '8e84eadb49b3d346087a0bfd2128d5d0'
    privategpt = PrivateChatbot(api_key)


    file_paths = ['doc1.pdf', 'doc2.pdf']


    print(privategpt.upload(file_paths, 0, 0))

