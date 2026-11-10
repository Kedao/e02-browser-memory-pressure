# E02 浏览器证明阶段的内存压力与耗时

320 MiB 内存软限额在两次独立对照中都让浏览器在证明阶段出现内存停顿。首批证明耗时中位数增加 **4.63%**，反向复测只增加 **1.29%**，且两对相邻块的变化方向不一致。**内存停顿可以复现，约 4.6% 的变慢没有复现。**

## 实测结果

| 软限额与顺序 | 无软限额 A，中位数（ms） | 施压 B，中位数（ms） | B 相对 A 的变化 | B 组有 `full` 停顿的证明窗口 |
| --- | ---: | ---: | ---: | ---: |
| 384 MiB，A → B → B → A | 1014.770 | 1010.545 | −0.42% | 5/10 |
| 320 MiB，A → B → B → A | 999.150 | 1045.385 | +4.63% | 8/10 |
| 320 MiB，B → A → A → B | 1003.595 | 1016.580 | +1.29% | 9/10 |

每批两组各有 10 条正式记录。A 组所有正式证明窗口的 `full` 增量均为零。三批含预热共 **72/72** 条证明验证通过且完成清理，控制组 OOM 计数为零。352 MiB 预试只有 3/5 个正式证明窗口测到停顿，未达到 4/5 的启动门槛。320 MiB 预试达到 4/5，另开浏览器做了正式对照。[384 MiB 汇总](data/formal/depth7-384mib-abba/aggregate.json) · [320 MiB 首批](data/formal/depth7-320mib-abba/aggregate.json) · [320 MiB 反向复测](data/formal/depth7-320mib-baab/aggregate.json) · [352 MiB 预试](data/smoke/pressure-352mib/gate.json) · [320 MiB 预试](data/smoke/pressure-320mib/gate.json)

320 MiB 首批的两对相邻块分别慢 3.65% 和 5.61%，反向复测的两对分别快 0.43% 和慢 3.77%。两批施压组的单轮 `full` 停顿中位数分别为 12.582 ms 和 10.619 ms。`full` 是控制组累计停顿，证明耗时由页面另行计时。[首批逐块记录](data/formal/depth7-320mib-abba/) · [反向复测逐块记录](data/formal/depth7-320mib-baab/)

## 实验方法与适用范围

测试使用一台 Linux 桌面和无头 Chrome 156，固定 Semaphore Noir 构建、电路深度 7 和请求 1 线程。各块实读跨源隔离和共享内存均可用。每块新建独立 Chrome 和 cgroup v2，先跑一次预热，再跑五次正式测量。A 的 `memory.high` 为 `max`，B 使用表中软限额，两组的 `memory.max` 均为 `max`。[Linux cgroup v2 内存指标](https://docs.kernel.org/admin-guide/cgroup-v2.html#memory)

证明耗时包含 witness 生成和生成证明，初始化、验证、轮间等待分别计时。用浏览器性能时标把控制组计数对齐到证明窗口，两端各留 10 ms，只对完整落入窗口的样本作差。采样间隔约 50 ms。内存计量涵盖测试控制组内的 Chrome 及启动它的自动化进程，无法从中分离单个证明 Worker 的停顿。两档限额分批测量，远端电路和公共数据的逐请求缓存命中及内容哈希未记录。结论限于本机、本构建及本次压力条件。[时标与数据字段](DATA.md)

## 复算归档数据

在此目录运行以下命令，使用 Python 标准库逐块复算压力读数、三批汇总和两次预试的启动门槛：

```bash
python3 scripts/recompute.py
```

命令可离线运行。归档包含 90 条逐轮记录，其中 72 条来自三批正式对照，18 条来自基线和预试。[正式数据](data/formal/) · [基线与预试](data/smoke/) · [字段与脱敏方式](DATA.md)

## 重建带时标的测试页面

使用 E01 的固定版本，加上本目录的时标补丁。构建完成后可以核对发布候选包保留的文件哈希。[E01 仓库](https://github.com/Kedao/e01-semaphore-noir-benchmark/tree/4d6fcb9c7c28fd50d93347900877bdeed814eae9) · [时标补丁](scripts/e01-proof-marks.patch) · [构建哈希](build-sha256.txt)

```bash
candidate=$PWD
git clone https://github.com/Kedao/e01-semaphore-noir-benchmark.git e01
git -C e01 checkout --detach 4d6fcb9c7c28fd50d93347900877bdeed814eae9
git -C e01 apply "$candidate/scripts/e01-proof-marks.patch"
cd e01
npm ci --ignore-scripts
npm run build
sha256sum -c "$candidate/build-sha256.txt"
```

用 E01 的本地隔离预览打开页面。将测试 Chrome 放入独立的 Linux cgroup v2，实际核对 `memory.high`、`memory.max` 和浏览器的隔离读数。采样从控制组外运行，把页面 Performance Timeline 的起止标记与控制组读数对齐。[控制组采样脚本](scripts/sample-cgroup.py) · [证明窗口复算脚本](scripts/summarize-proof-windows.py)
