import * as vscode from 'vscode';
import * as path from 'path';
import { spawn } from 'child_process';
import { promisify } from 'util';
import { exec } from 'child_process';

const execAsync = promisify(exec);

interface CommitResult {
    commit_message?: string;
    success: boolean;
    error?: string;
}

export function activate(context: vscode.ExtensionContext) {
    console.log('Auto Commit Messages (Python) extension is now active');

    // Register commands
    const generateCommand = vscode.commands.registerCommand('autoCommitMessages.generate', async () => {
        await generateCommitMessage(context);
    });

    const setupCommand = vscode.commands.registerCommand('autoCommitMessages.setup', async () => {
        await setupPythonEnvironment(context);
    });

    context.subscriptions.push(generateCommand, setupCommand);

    // Check Python setup on activation
    checkPythonSetup(context);
}

async function checkPythonSetup(context: vscode.ExtensionContext) {
    const config = vscode.workspace.getConfiguration('autoCommitMessages');
    const pythonPath = config.get<string>('pythonPath') || 'python';
    
    try {
        const scriptPath = path.join(context.extensionPath, 'python', 'commit_generator.py');
        const { stderr } = await execAsync(`${pythonPath} -c "import sys; print(sys.version)"`);
        
        if (stderr) {
            throw new Error('Python not found or not working');
        }
        
        // Check if required packages are installed
        try {
            await execAsync(`${pythonPath} -c "import langgraph, google.generativeai"`);
        } catch (error) {
            const result = await vscode.window.showWarningMessage(
                'Python dependencies are not installed. Would you like to install them now?',
                'Install Dependencies',
                'Not Now'
            );
            
            if (result === 'Install Dependencies') {
                await setupPythonEnvironment(context);
            }
        }
    } catch (error) {
        vscode.window.showErrorMessage(
            'Python is not available. Please install Python and configure the path in settings.',
            'Open Settings'
        ).then(result => {
            if (result === 'Open Settings') {
                vscode.commands.executeCommand('workbench.action.openSettings', 'autoCommitMessages.pythonPath');
            }
        });
    }
}

async function setupPythonEnvironment(context: vscode.ExtensionContext) {
    const config = vscode.workspace.getConfiguration('autoCommitMessages');
    const pythonPath = config.get<string>('pythonPath') || 'python';
    
    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: "Setting up Python environment...",
        cancellable: false
    }, async (progress) => {
        try {
            progress.report({ increment: 20, message: "Checking Python..." });
            
            // Check Python version
            const { stdout } = await execAsync(`${pythonPath} --version`);
            console.log('Python version:', stdout);
            
            progress.report({ increment: 30, message: "Installing dependencies..." });
            
            // Install requirements
            const requirementsPath = path.join(context.extensionPath, 'py', 'requirements.txt');
            await execAsync(`${pythonPath} -m pip install -r "${requirementsPath}"`);
            
            progress.report({ increment: 50, message: "Verifying installation..." });
            
            // Verify installation
            await execAsync(`${pythonPath} -c "import langgraph, google.generativeai; print('All packages installed successfully')"`);
            
            vscode.window.showInformationMessage('Python environment setup completed successfully!');
            
        } catch (error) {
            console.error('Setup error:', error);
            vscode.window.showErrorMessage(`Failed to setup Python environment: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    });
}

async function generateCommitMessage(context: vscode.ExtensionContext) {
    try {
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        if (!workspaceFolder) {
            vscode.window.showErrorMessage('No workspace folder found. Please open a project.');
            return;
        }

        const config = vscode.workspace.getConfiguration('autoCommitMessages');
        const apiKey = config.get<string>('googleApiKey');

        if (!apiKey) {
            const result = await vscode.window.showErrorMessage(
                'Google AI API Key is not configured. Please set it in settings.',
                'Open Settings'
            );
            if (result === 'Open Settings') {
                vscode.commands.executeCommand('workbench.action.openSettings', 'autoCommitMessages.googleApiKey');
            }
            return;
        }

        await vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: "Generating commit message with AI...",
            cancellable: true
        }, async (progress, token) => {
            const pythonPath = config.get<string>('pythonPath') || 'python';
            const scriptPath = path.join(context.extensionPath, 'py', 'commit_generator.py');
            
            const args = [
                scriptPath,
                workspaceFolder.uri.fsPath,
                '--api-key', apiKey,
                '--model', config.get<string>('model') || 'gemini-1.5-flash',
                '--temperature', (config.get<number>('temperature') || 0.3).toString(),
                '--max-tokens', (config.get<number>('maxTokens') || 100).toString(),
                '--json'
            ];

            progress.report({ increment: 20, message: "Analyzing git changes..." });

            const result = await runPythonScript(pythonPath, args, token);
            
            if (token.isCancellationRequested) {
                return;
            }

            progress.report({ increment: 60, message: "Processing AI response..." });

            if (result.success && result.commit_message) {
                progress.report({ increment: 20, message: "Applying commit message..." });
                
                // Set the commit message in the Source Control input box
                const gitExtension = vscode.extensions.getExtension('vscode.git')?.exports;
                const git = gitExtension?.getAPI(1);
                
                if (git && git.repositories.length > 0) {
                    const repo = git.repositories[0];
                    repo.inputBox.value = result.commit_message;
                    vscode.window.showInformationMessage(`Generated: "${result.commit_message}"`);
                } else {
                    // Fallback: copy to clipboard
                    await vscode.env.clipboard.writeText(result.commit_message);
                    vscode.window.showInformationMessage(
                        `Generated (copied to clipboard): "${result.commit_message}"`
                    );
                }
            } else {
                const errorMessage = result.error || 'Failed to generate commit message';
                if (errorMessage.includes('No changes detected')) {
                    vscode.window.showWarningMessage('No changes detected to generate commit message.');
                } else {
                    vscode.window.showErrorMessage(`Error: ${errorMessage}`);
                }
            }
        });

    } catch (error) {
        console.error('Error in generateCommitMessage:', error);
        vscode.window.showErrorMessage(
            `Failed to generate commit message: ${error instanceof Error ? error.message : 'Unknown error'}`
        );
    }
}

function runPythonScript(pythonPath: string, args: string[], token: vscode.CancellationToken): Promise<CommitResult> {
    return new Promise((resolve, reject) => {
        const process = spawn(pythonPath, args);
        let stdout = '';
        let stderr = '';

        // Handle cancellation
        token.onCancellationRequested(() => {
            process.kill();
            reject(new Error('Operation was cancelled'));
        });

        process.stdout.on('data', (data) => {
            stdout += data.toString();
        });

        process.stderr.on('data', (data) => {
            stderr += data.toString();
        });

        process.on('close', (code) => {
            if (code === 0) {
                try {
                    // Find the JSON part in the output
                    const jsonStart = stdout.lastIndexOf('{');
                    const jsonPart = stdout.substring(jsonStart);
                    const result: CommitResult = JSON.parse(jsonPart);
                    resolve(result);
                } catch (error) {
                    reject(new Error(`Failed to parse Python script output: ${stdout}`));
                }
            } else {
                reject(new Error(`Python script failed with code ${code}: ${stderr}`));
            }
        });

        process.on('error', (error) => {
            reject(new Error(`Failed to start Python script: ${error.message}`));
        });
    });
}

export function deactivate() {
    console.log('Auto Commit Messages (Python) extension is now deactivated');
}