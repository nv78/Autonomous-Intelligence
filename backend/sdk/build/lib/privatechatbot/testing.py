import time
#from anoteai import PrivateChatbot
from core import PrivateChatbot

if __name__ == "__main__":
    api_key = 'f9a7030ac30ff879b8d3b15ad49b5234'
    privategpt = PrivateChatbot(api_key)

    file_paths = ['doc1.pdf', 'doc2.pdf']

    #chat_id = privategpt.upload(file_paths, 0, 0)['id']
    #message_id = privategpt.chat(chat_id, "What is this paper classification performance about?")['message_id']
    # print("output from upload: ", privategpt.upload(task_type=1, model_type=0, file_paths=file_paths))
    # chat_id = privategpt.upload(task_type=1, model_type=0, file_paths=file_paths))['id']
    # print("output from chat: ", privategpt.chat(3, "What is this paper classification performance about?", finetuned_model_key="ft:gpt-4o-mini-0613:personal:anote:8DO8V2LB"))
    # print("output from evaluate:", privategpt.evaluate(6))


    #chat_id = privategpt.upload(task_type=0, model_type=1, file_paths=file_paths)['id']
    # res = privategpt.chat(13, "What is this paper classification performance about?", finetuned_model_key="ft:gpt-4o-mini-0613:personal:anote:8DO8V2LB")
    # print(res)
    # message_id = res['message_id']
    # print(privategpt.evaluate(message_id))

    #chat_id = privategpt.upload(task_type="edgar", model_type="gpt", ticker="aapl")['id']

    chat_id = privategpt.upload(task_type="documents", model_type="gpt", file_paths=file_paths)['id']

    response = privategpt.chat(chat_id, "Who is the research paper Improving Classification Performance written by?")
    print(response)

    message_id = response['message_id']
    print(privategpt.evaluate(message_id))






    #print(privategpt.chat(100005, "What is the text classification performance about?"))


