# YARTAT - Yet Another REALITY Auto Translation

YARTAT is a powerful real-time translation tool specifically designed for the REALITY app, providing seamless translation capabilities for live chat messages. It supports multiple translation engines and features an intuitive text-based user interface (TUI).

## Features

- Real-time message translation
- Multiple translation engine support:
  - Google Translate
  - OpenAI and OpenAI-compatible endpoints (Gemini, DeepSeek, etc.)
- Text-based user interface (TUI) with live status display
- Multi-language support with i18n
- Translation caching for improved performance
- Configurable target languages
- Automatic language detection
- Smart translation filtering (emojis, numbers, etc.)

## Requirements

- Python 3.11 or higher
- Required packages (listed in requirements.txt)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/not-hanjo-mei/YARTAT.git
   cd YARTAT
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a configuration file:
   ```bash
   cp config.json.example config.json
   ```

4. Edit `config.json` to set up all required configuration values. The following settings are essential for the application to function:

   **Reality App Settings:**
   - `reality.mediaId` - Your Reality App Media ID
   - `reality.vLiveId` - Reality App Live ID
   - `reality.gid` - Reality App GID
   - `reality.auth` - Reality App Authentication Token

   **Translation Settings:**
   - `translation.targetLanguage` - Target language for translations (e.g., "en-US")
   - `translation.engine` - Translation engine to use ("google" or "openai")

   **OpenAI Settings (if using OpenAI engine):**
   - `openai.apiKey` - Your OpenAI API key
   - `openai.apiBase` - API base URL (for OpenAI or compatible endpoints)
   - `openai.model` - AI model name to use

   **Performance Settings (optional):**
   - `performance.maxWorkers` - Translation thread pool size (default: 1)
   - `performance.translationTimeout` - Translation timeout in seconds (default: 30)

## Usage

1. Start the application:
   ```bash
   python main.py
   ```

2. The TUI interface will display:
   - Connection status
   - Current translation engine
   - Target language
   - AI model
   
3. Available keyboard shortcuts in TUI mode:
   - `h` - Show help
   - `c` - Show/edit configuration
   - `q` - Quit application

### Supported Languages

- English (en-US)
- Simplified Chinese (zh-CN)
- Traditional Chinese (zh-TW)
- Japanese (ja-JP)
- Russian (ru-RU)
- Ukrainian (uk-UA)
- And more...

## ~~Super Earth~~ YARTAT Recruitment Announcement

> *MISCOMMUNICATION DETECTED*

Haha, look familiar?  
Scenes like these happen all over REALITY, **RIGHT NOW**!  
**YOU** could be next --
That is unless you make **THE MOST IMPORTANT DECISION OF YOUR LIFE**...  

Prove to yourself that you have the **STRENGTH** and the **COURAGE** to break language barriers.  
Use... the YARTAT!  

Become part of an elite translation force!  
Decipher exotic new languages!  
And spread Managed Understanding throughout REALITY!  

**Become a hero,  
Become a legend,  
Become a YARTAT!**

## Contributing

Contributions are welcome! Please feel free to submit pull requests.

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.