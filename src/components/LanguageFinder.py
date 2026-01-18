import os

class LanguageFinder:
    """
    Detects the programming language of a file based on its extension.
    """

    EXTENSION_MAP = {
        '.ts': 'typescript',
        '.java': 'java',
        '.py': 'python',
        '.cs': 'c_sharp',
        '.js': 'javascript',
        '.go': 'go',
        '.php': 'php',
        '.cpp': 'cpp',
        '.cc': 'cpp',
        '.cxx': 'cpp',
        '.h': 'cpp',
        '.hpp': 'cpp'
    }

    def detect(self, file_path: str) -> str:
        """
        Detects the language of the given file path.
        Returns the language name or 'unknown'.
        """
        _, ext = os.path.splitext(file_path)
        return self.EXTENSION_MAP.get(ext.lower(), 'unknown')
