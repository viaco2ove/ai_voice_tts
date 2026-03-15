# 创建 3.11.9 (wsl or  windows)
conda create -n py3119 python=3.11.9 -y
conda activate py3119
python -V   # 应该是 Python 3.11.9

# wsl
python -m venv .venv_wsl

## 退出 conda（避免混用）
conda deactivate

## 启用 venv_wsl
source .venv_wsl/bin/activate
python -V   # 仍然应是 3.11.9

# windows
python -m venv .venv

## 退出 conda（避免混用）
conda deactivate

## 启用 venv
.venv\Scripts\activate


# 安装依赖
pip install -r requirements.txt

