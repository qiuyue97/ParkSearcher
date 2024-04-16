import subprocess

def run_baidu_api(times):
    for _ in range(times):
        try:
            # 使用subprocess运行baidu_api.py，并等待其完成
            # 假设baidu_api.py位于同一目录下
            completed_process = subprocess.run(['python', 'baidu_api.py'], check=True)
            print(f"baidu_api.py运行完成，退出码: {completed_process.returncode}")
        except subprocess.CalledProcessError as e:
            # 如果baidu_api.py非正常退出（即返回非0退出码），将捕获到异常
            print(f"baidu_api.py运行异常退出，退出码: {e.returncode}")
        except Exception as e:
            # 捕获其他所有可能的异常
            print(f"运行baidu_api.py时发生错误: {e}")
        finally:
            print("一次baidu_api.py运行结束，准备开始下一次...\n")

# 设置循环运行的次数
loop_times = 1000

if __name__ == "__main__":
    run_baidu_api(loop_times)
