# Auto Commit Messages (Python + LangGraph)

A VS Code extension that automatically generates intelligent commit messages using Python, Google's Gemini AI, and LangGraph workflow orchestration.

## 🌟 Features

- 🐍 **Python Backend**: Leverages the full Python ecosystem for AI processing
- 🤖 **Google Gemini AI**: Uses state-of-the-art language models
- 🔄 **LangGraph Workflow**: Sophisticated multi-step analysis pipeline
- 📝 **Conventional Commits**: Follows standard commit message format
- ⚡ **Smart Integration**: Seamlessly integrates with VS Code's Git interface
- 🎯 **Context-Aware**: Analyzes code changes, file types, and project structure

## 🚀 Installation

### Prerequisites
- **Node.js 16+**
- **Python 3.8+**
- **VS Code**
- **Google AI API Key** ([Get one here](https://makersuite.google.com/app/apikey))

### Setup Steps

1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd vscode-auto-commit-messages
   ```

2. **Install Node.js Dependencies**
   ```bash
   npm install
   ```

3. **Setup Python Environment**
   ```bash
   cd py
   pip install -r requirements.txt
   cd ..
   ```

4. **Configure API Key**
   - Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Create `py/.env` file:
     ```bash
     cp py/.env.example py/.env
     # Edit .env and add: GOOGLE_API_KEY=your_api_key_here
     ```

5. **Build the Extension**
   ```bash
   npm run compile
   ```

6. **Test the Extension**
   - Press `F5` in VS Code to launch Extension Development Host
   - Open a test repository in the new window
   - Make some changes and test the extension

## ⚙️ Configuration

Open VS Code Settings (`Ctrl+,`) and configure:

| Setting | Description | Default |
|---------|-------------|---------|
| `autoCommitMessages.googleApiKey` | Your Google AI API key *(required)* | - |
| `autoCommitMessages.model` | AI model to use | `gemini-1.5-flash` |
| `autoCommitMessages.temperature` | Generation creativity (0.0-1.0) | `0.3` |
| `autoCommitMessages.maxTokens` | Maximum response length | `100` |
| `autoCommitMessages.pythonPath` | Path to Python executable | `python` |

### Available Models
- `gemini-1.5-flash` - Fast, efficient (recommended)
- `gemini-1.5-pro` - More capable, slower
- `gemini-pro` - Legacy model

## 📖 Usage

### Method 1: Source Control Panel
1. Make changes to your code
2. Open Source Control panel (`Ctrl+Shift+G`)
3. Click the **"Generate Commit Message"** button
4. The AI-generated message appears in the commit input box

### Method 2: Command Palette
1. Press `Ctrl+Shift+P`
2. Type **"Auto Commit: Generate Commit Message"**
3. Press Enter

### Method 3: Direct Python Usage
```bash
cd py
python commit_generator.py /path/to/your/repo --api-key YOUR_API_KEY
```

## 🧠 How It Works

The extension uses a sophisticated **LangGraph workflow** with four steps:

### 1. **Analyze Diff** 🔍
- Examines git diff of staged/modified files
- Identifies change patterns and affected modules
- Understands the scope and impact of changes

### 2. **Determine Type** 🏷️
- Categorizes changes using conventional commit types
- Determines appropriate scope (component/module)
- Uses AI reasoning with smart fallbacks

### 3. **Generate Message** ✍️
- Creates conventional commit message
- Uses imperative mood and proper formatting
- Keeps messages concise yet descriptive

### 4. **Refine Message** ✨
- Ensures compliance with conventions
- Handles edge cases and provides fallbacks
- Optimizes message length (up to 95 characters)

## 📋 Commit Types & Examples

| Type | Usage | Example |
|------|-------|---------|
| `feat` | New features | `feat(auth): add OAuth2 login support` |
| `fix` | Bug fixes | `fix(api): resolve null pointer exception` |
| `docs` | Documentation | `docs: update installation guide` |
| `style` | Code formatting | `style: fix indentation in utils` |
| `refactor` | Code restructuring | `refactor(db): extract connection logic` |
| `perf` | Performance improvements | `perf(query): optimize user search` |
| `test` | Adding/updating tests | `test(auth): add login flow tests` |
| `chore` | Maintenance tasks | `chore: update dependencies` |
| `ci` | CI/CD changes | `ci: add automated testing` |
| `build` | Build system changes | `build: update webpack config` |

## 🛠️ Development

### Project Structure
```
vscode-auto-commit-messages/
├── src/                          # VS Code extension source
│   └── extension.ts             # Main extension logic
├── py/                          # Python backend
│   ├── commit_generator.py      # Main Python script with LangGraph
│   ├── requirements.txt         # Python dependencies
│   ├── .env.example            # Environment variables template
│   └── .env                    # Your environment variables
├── package.json                # Extension manifest
├── tsconfig.json              # TypeScript configuration
└── README.md                  # This file
```

### Building & Testing
```bash
# Install dependencies
npm install
cd py && pip install -r requirements.txt && cd ..

# Compile TypeScript
npm run compile

# Test Python script directly
cd py
python commit_generator.py . --api-key YOUR_KEY --json

# Launch VS Code extension development
# Press F5 in VS Code
```

### Adding Features
1. **Python Logic**: Modify `py/commit_generator.py` for AI processing
2. **VS Code Integration**: Update `src/extension.ts` for UI features
3. **Settings**: Add new options in `package.json` configuration section

## 🔧 Troubleshooting

### Common Issues

**Python not found**
```bash
# Check Python installation
python --version

# Set custom Python path in VS Code settings
"autoCommitMessages.pythonPath": "/path/to/python"
```

**Missing dependencies**
```bash
cd py
pip install -r requirements.txt
```

**API key issues**
- Verify your Google AI API key is correct
- Check internet connection
- Ensure API key has proper permissions

**No changes detected**
```bash
# Check git status
git status

# Make sure you have uncommitted changes
echo "test" >> README.md
```

### Debug Mode
Run the Python script directly to debug issues:
```bash
cd py
python commit_generator.py . --api-key YOUR_KEY --model gemini-1.5-flash
```

Check VS Code Developer Console (`Help > Toggle Developer Tools`) for extension logs.

## 🎯 Best Practices

### For Best Results:
- **Make focused commits** - smaller, logical changes work better
- **Stage related files** - group related changes together  
- **Review generated messages** - edit them if needed
- **Use descriptive branch names** - helps with context

### Customization Tips:
- **Lower temperature** (0.1-0.2) for more consistent messages
- **Higher temperature** (0.4-0.6) for more creative descriptions
- **Increase max tokens** for longer, more detailed messages

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Test thoroughly
5. Commit with conventional messages (use the extension!)
6. Push and open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [LangGraph](https://github.com/langchain-ai/langgraph) for workflow orchestration
- [Google AI](https://ai.google.dev/) for the Gemini models
- [Conventional Commits](https://www.conventionalcommits.org/) for commit standards
- [VS Code Extension API](https://code.visualstudio.com/api) for seamless integration

---

**Generate meaningful commit messages effortlessly!** 🚀
