## Chatgpt-FastAPI 

[中文](./README_CN.md)

If you are a Python person, and looking for a simple web interface to try out OpenAI chatgpt API, then this is the repo for you. 

This is a Python one-stop shop project that I built myself to try out different context/prompt engineering. I hope you will find it useful.

## System Requirement

Tested on `MacOS` and `Ubuntu20 LTS`

Python version `== python3.8`

<i>Technically, it should work on `>= python3.7`, but you will have to edit the module versions accordingly in `install.sh` file</i>

## Installation
1. At project root, create and enter a `python3.8` virtual environment
```
cd $PROJECT_ROOT
python3.8 -m venv venv
source venv/bin/activate
```

2. One bash script installation for all
```
bash ./install.sh
```

## Start Server

Visit openai to obtain your [API key](https://platform.openai.com/account/api-keys) and [Organization ID](https://platform.openai.com/account/org-settings)

Then export to env variable
```
export OPENAI_API_KEY="sk-abcdef..."
export OPENAI_ORG_ID="org-zxcvbb..."
```

Start the server using bash script
```
bash ./app.sh start --host 0.0.0.0 --port 8080
```

You should see the below sample stdout
```
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
chatgpt launched
--------------------------
```

Note that this server is detached from your terminal, you're free to close the terminal without interrupting the service.

To stop the server, execute `bash ./app.sh stop`

Now, open web browser and visit http://0.0.0.0:8080. Enjoy

![image](./doc/sample1_en.png)

## Switch Language

<br>Step 1: create your own `config_lang.py`, similar to the following files
```
./config
├── config_en.py
└── config_zh.py
```

<br>Step 2: change the import in `main.py:32` accordingly
```
from config.config_en import Args
# from config.config_zh import Args
```

<br>Step 3: create your own prompts, arranging the files in the following way
```
./prompts
├── prompts_en
│   ├── chat-agent.txt
│   └── context-summarizer.txt
└── prompts_zh
    ├── chat-agent.txt
    └── context-summarizer.txt
```

<br>Step 4: edit the `config_lang.py` created in step 1, make sure its `PROMPTS_DIR` is assigned with the intended directory. Also edit all the message related variables (line 30:50). Replace them with your desired texts.


## Common Issues
to be added

## Credits
1. This project was built upon <br> https://medium.com/@ahtishamshafi9906/how-to-build-a-simple-chat-application-in-fastapi-7bafad755654
2. Spinning donut <br> https://www.a1k0n.net/2011/07/20/donut-math.html

## License

This project is licensed under the [MIT License](LICENSE).