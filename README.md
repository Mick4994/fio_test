# SSD 性能测试工具

这是一个使用 FIO (Flexible I/O Tester) 对 SSD 进行性能测试的 Python 脚本。该脚本提供了一个简单的命令行界面，用于配置和运行各种 SSD 性能测试。

## 前提条件

- Python 3.6+
- FIO 工具已安装

在大多数 Linux 发行版上，可以使用包管理器安装 FIO：

```bash
# Debian/Ubuntu
sudo apt-get install fio
# CentOS/RHEL
sudo yum install fio
# Arch Linux
sudo pacman -S fio
```

## 使用方法

基本用法：

```bash
python script.py --device /dev/sdX
```

其中 `/dev/sdX` 是您要测试的 SSD 设备路径。

### 命令行参数

| 参数 | 描述 | 默认值 | 可选值/范围 |
|------|------|--------|------------|
| `--device` | 要测试的设备路径 | 必填 | 例如：`/dev/sda`、`/dev/nvme0n1` |
| `--size` | 测试文件大小 | `1G` | 例如：`512M`、`1G`、`10G` |
| `--rw` | 读写模式 | `randread` | `read`、`write`、`randread`、`randwrite`、`randrw` |
| `--bs` | 块大小 | `4k` | 例如：`4k`、`8k`、`64k`、`1M` |
| `--iodepth` | IO 队列深度 | `32` | 1-256，SSD 通常使用 32-64 |
| `--numjobs` | 并发任务数 | `4` | 1-64，取决于 CPU 核心数 |
| `--runtime` | 测试运行时间(秒) | `60` | 10-3600，时间越长结果越准确 |

### 参数详解

#### 读写模式 (`--rw`)

- `read`: 顺序读取
- `write`: 顺序写入
- `randread`: 随机读取
- `randwrite`: 随机写入
- `randrw`: 混合随机读写

#### 块大小 (`--bs`)

块大小决定了每次 I/O 操作的数据量。不同的块大小适用于不同的场景：

- 小块大小 (4k-8k): 模拟数据库、操作系统等小文件随机访问
- 中等块大小 (64k-128k): 模拟混合工作负载
- 大块大小 (512k-1M): 模拟大文件传输、视频流等顺序访问

#### IO 队列深度 (`--iodepth`)

IO 队列深度表示同时发送到设备的 I/O 请求数量。SSD 通常在较高的队列深度下性能更好：

- 低队列深度 (1-4): 模拟轻负载应用
- 中等队列深度 (8-16): 模拟普通服务器负载
- 高队列深度 (32-64): 模拟高负载服务器、数据库等

#### 并发任务数 (`--numjobs`)

并发任务数表示同时运行的 FIO 进程数。通常设置为 CPU 核心数或略低。

## 示例

### 随机读测试

```bash
python script.py --device /dev/nvme0n1 --rw randread --bs 4k --iodepth 32 --numjobs 4 --runtime 60
```

### 随机写测试

```bash
python script.py --device /dev/nvme0n1 --rw randwrite --bs 4k --iodepth 32 --numjobs 4 --runtime 60
```

### 混合随机读写测试

```bash
python script.py --device /dev/nvme0n1 --rw randrw --bs 4k --iodepth 32 --numjobs 4 --runtime 60
```

### 顺序读测试

```bash
python script.py --device /dev/nvme0n1 --rw read --bs 4k --iodepth 32 --numjobs 4 --runtime 60
``` 

### 顺序写测试

```bash
python script.py --device /dev/nvme0n1 --rw write --bs 4k --iodepth 32 --numjobs 4 --runtime 60
```


## 注意事项

1. 在生产环境中使用时请小心，测试可能会对设备上的数据造成损坏
2. 建议在测试前备份重要数据
3. 对于更准确的结果，建议运行多次测试并取平均值
4. 测试结果会以 JSON 格式保存在脚本运行目录下
