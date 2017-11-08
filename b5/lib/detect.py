import os


def detect_git(path):
    git_path = os.path.join(path, '.git')
    return os.path.exists(git_path) and os.path.isdir(git_path)


DETECT = {
    'git': detect_git,
}
