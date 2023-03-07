import os
import time
import traceback
from typing import Literal
from datetime import datetime

import openai
import tiktoken
from colorama import Fore, Style


def time_now_str(): return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def warn(text: str): print(f"{Fore.RED}{text}{Style.RESET_ALL}")


class ChatGPT(object):
    MAX_TOKENS: int = 4096
    REPLY_COST: int = 2   # every reply is primed with <im_start>assistant, minus 2
    MIN_TOKEN_PER_MSG: int = 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n

    def __init__(self,
                 *,
                 api_key: str,
                 api_org: str,
                 prompts_dir: str = './prompts',
                 model_name: Literal['gpt-3.5-turbo', 'gpt-3.5-turbo-0301'] = 'gpt-3.5-turbo-0301',
                 temperature: float = 1.,
                 min_reply_tokens: int = 800,
                 network_err_text: str = '[encountering unknown network error]',
                 ):
        """

        :param api_key:
        :param api_org:
        :param prompts_dir:
        :param model_name:
        :param temperature:
        """
        assert model_name in ['gpt-3.5-turbo', 'gpt-3.5-turbo-0301'], \
            f"'model_name' must be one of ['gpt-3.5-turbo', 'gpt-3.5-turbo-0301'] but received '{model_name}'"
        self.model_name = model_name
        assert os.path.exists(prompts_dir), f"prompts_dir '{prompts_dir}' is not found!"
        self.prompts_dir: str = prompts_dir
        self.temperature: float = temperature  # 0.0 ~ 1.0
        self.min_reply_tokens = min_reply_tokens
        self.max_tokens: int = self.MAX_TOKENS - self.REPLY_COST - self.min_reply_tokens

        self.tokenizer = self.load_tokenizer(self.model_name)
        self.prompts_dict = self.load_prompts_dict()
        self.network_err_text = network_err_text

        if api_key is not None:
            openai.api_key = api_key
        if api_org is not None:
            openai.organization = api_org

    def load_prompts_dict(self):
        prompt_fnames = os.listdir(self.prompts_dir)
        if '.DS_Store' in prompt_fnames:
            prompt_fnames.remove('.DS_Store')

        prompts_dict = {}
        for fname in prompt_fnames:
            prompts_dict[fname] = os.path.join(self.prompts_dir, fname)
        return prompts_dict

    def get_prompt(self, prompt: str):
        prompts_dict = self.prompts_dict
        if prompt in prompts_dict:
            with open(prompts_dict[prompt], 'r') as f:
                return ''.join(f.readlines())
        else:
            self.prompts_dict = prompts_dict = self.load_prompts_dict()
            if prompt in prompts_dict:
                with open(prompts_dict[prompt], 'r') as f:
                    return ''.join(f.readlines())
            else:
                warn(f"prompt file '{prompt}' under directory '{self.prompts_dir}'")
                return ''

    def launch_chatgpt(self):
        model_name = self.model_name
        status = False

        # noinspection PyBroadException
        try:
            model_list = openai.Model.list().data
            for model_info in model_list:
                if model_info.id == model_name:
                    status = True
                    break
        except Exception:
            traceback.print_exc()
        return status

    @staticmethod
    def load_tokenizer(model_name):
        try:
            tokenizer = tiktoken.encoding_for_model(model_name)
        except KeyError:
            tokenizer = tiktoken.get_encoding("cl100k_base")
        return tokenizer

    def encode_tokens(self, text: str):
        tokens = self.tokenizer.encode(text)
        return tokens

    def decode_tokens(self, tokens):
        return self.tokenizer.decode(tokens)

    def count_context_tokens(self, context: list):
        """
        reference
        https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb
        under section: 6. Counting tokens for chat API calls

        See https://github.com/openai/openai-python/blob/main/chatml.md for information on how
        messages are converted to tokens.
        """
        min_token_per_msg = self.MIN_TOKEN_PER_MSG
        num_tokens_list = []
        for message in context:
            num_tokens = min_token_per_msg  # every message follows <im_start>{role/name}\n{content}<im_end>\n
            for key, value in message.items():
                num_tokens += len(self.tokenizer.encode(value))
                if key == "name":  # if there's a name, the role is omitted
                    num_tokens += -1  # role is always required and always 1 token
            num_tokens_list.append(num_tokens)
        # num_tokens_list.append(self.REPLY_COST)  # every reply is primed with <im_start>assistant
        return num_tokens_list

    def __send_message_stream__(self, context: list):
        """
        Args:
            context:
                    [
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": "Who won the world series in 2020?"},
                        {"role": "assistant", "content": "The Los Angeles Dodgers won the World Series in 2020."},
                    ]
        Return:
             content: string
             status:  bool, True upon final return
        """

        # noinspection PyBroadException
        try:
            model_name = self.model_name
            temperature = self.temperature

            iterator = openai.ChatCompletion.create(
                model=model_name,
                stream=True,
                temperature=temperature,  # 0.0 ~ 1.0
                # max_tokens=4096,  # <= 4096
                messages=context
            )

            for res in iterator:
                choice = res.choices[0]
                delta = choice.delta
                # finish_reason = choice.finish_reason
                status = choice.finish_reason is not None
                if len(delta) > 0 and "content" in delta:
                    content = delta.content
                    yield content, status
                if status:
                    break

        except Exception as err:
            traceback.print_exc()
            print('exception text')
            print(str(err))
            print(f'context token size: {self.count_context_tokens(context)}')
            content = self.network_err_text
            status = True
            yield content, status
        finally:
            pass

    def __send_message__(self, context: list):
        model_name = self.model_name
        temperature = self.temperature

        res = openai.ChatCompletion.create(
            model=model_name,
            stream=False,
            temperature=temperature,  # 0.0 ~ 1.0
            # max_tokens=4096,  # <= 4096
            messages=context
        )
        content: str = res.choices[0].message.content
        return content

    @staticmethod
    def create_context(text: str):
        context = [
            {"role": "user", "content": str(text)},
        ]
        return context

    @staticmethod
    def update_context(context: list, content: str):
        context.append({'role': 'assistant', 'content': str(content)})
        return context

    def consolidate_context(self,
                            context: list,
                            keep_left: int = 2,
                            keep_right: int = 1,
                            max_try: int = 3):
        max_tokens: int = self.max_tokens
        num_tokens_list = self.count_context_tokens(context)
        if sum(num_tokens_list) < max_tokens:
            return context

        '''
        summarize aged messages
        '''
        summary_request: str = self.get_prompt('context-summarizer.txt')
        summary_req_context: list = [{'role': 'system', 'content': summary_request}]
        summary_req_n_tokens: int = sum(self.count_context_tokens(summary_req_context))
        try_i = 1
        while sum(num_tokens_list) >= max_tokens:
            if try_i > max_try:
                raise ValueError(f"""\
Hitting max_try({max_try}) while trying to consolidate context.
Consider changing the parameters "keep_left" and "keep_right",
as well as reducing length of the prompts.""")

            left_queue: list = context
            left_tokens_list = num_tokens_list
            right_queue: list = []
            right_tokens_list = []
            ''' [1] save messages that are not to be altered'''
            for _ in range(keep_right):
                right_queue.insert(0, left_queue.pop(-1))
                right_tokens_list.insert(0, left_tokens_list.pop(-1))
            ''' [2] keep moving messages from left to right until a summary request can be executed '''
            while sum(left_tokens_list) + summary_req_n_tokens > max_tokens:
                right_queue.insert(0, left_queue.pop(-1))
                right_tokens_list.insert(0, left_tokens_list.pop(-1))
            ''' [3] summarize '''
            context = left_queue + summary_req_context
            summarized_content = self.__send_message__(context)
            summarized_context = [{'role': 'system', 'content': summarized_content}]
            ''' [4] putting back context messages from the queues '''
            context = left_queue[:keep_left] + summarized_context + right_queue
            num_tokens_list = self.count_context_tokens(context)
            try_i += 1
        return context

    def send_message(self,
                     *,
                     text: str = None,
                     context: list = None,
                     stream: bool = False,
                     ):
        """
        Args:

            text:       query text
            context:    list of dictionaries specifying {"role": "system"/"user"/"assistant", "content": strings}
            stream:     bool

        Yield (if stream) or Return (if not stream):

            content:        str
            status:         bool, stopping signal, currently not implemented
            context:        updated context
            full_content:   str
        """
        if text is None and context is None:
            raise ValueError(f"either 'text' or 'context' needs to be provided")
        if (text is not None) and len(text) > 0:
            _context = self.create_context(text)
            if (context is not None) and isinstance(context, list):
                context += _context
            else:
                context = _context
        if (context is None) or (not isinstance(context, list)):
            raise ValueError(f"unknown context value: {context}")
        context = self.consolidate_context(context, keep_right=1)

        '''
        [1] send request、receive text
        '''
        if stream:
            content_list = []
            for content, _ in self.__send_message_stream__(context):
                content_list.append(content)
                yield content, False, context, None
            full_content = ''.join(content_list)
        else:
            full_content = self.__send_message__(context)

        '''
        [2] consolidate context
        '''
        context = self.update_context(context, full_content)
        context = self.consolidate_context(context, keep_right=1)

        '''
        [3] return 
        '''
        content = ''
        status: bool = True
        context: list = context
        full_content: str = full_content
        if stream:
            yield content, status, context, full_content
        else:
            return content, status, context, full_content


class ChatGPTDebug(ChatGPT):
    def __init__(self,
                 *args,
                 **kwargs,
                 ):
        super().__init__(*args, **kwargs)
        self.reply_text = '''\
1. sample text
    2. sample text
3. sample text
    4. sample text
5. sample text
    6. sample text
7. sample text
    8. sample text
9. sample text
    10. sample text
11. sample text
    12. sample text
```python
print('hello world')
```
```html
<head>
  <link rel="stylesheet" href="prismjs/themes/prism.css" />
  <script src="prismjs/prism.js"></script>
</head>
```'''

    def send_message(self,
                     *,
                     text: str = None,
                     context: list = None,
                     stream: bool = False,
                     ):
        """
        Args:

            text:       query text
            context:    list of dictionaries specifying {"role": "system"/"user"/"assistant", "content": strings}
            stream:     bool

        Yield (if stream) or Return (if not stream):

            content:        str
            status:         bool, stopping signal, currently not implemented
            context:        updated context
            full_content:   str
        """
        reply_text = self.reply_text

        '''
        [1] send request、receive text
        '''
        full_content = reply_text
        if stream:
            text_ls = reply_text.split('\n')
            for content in text_ls:
                content = '\n' + content
                yield content, False, context, None
                time.sleep(0.5)

        '''
        [3] return 
        '''
        content = ''
        status: bool = True
        context: list = context
        full_content: str = full_content
        if stream:
            yield content, status, context, full_content
        else:
            return content, status, context, full_content
