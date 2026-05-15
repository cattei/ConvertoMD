# MD转换神器 - 代码改进规划文档

## 📋 概述

本规划文档旨在修复代码审查中发现的所有问题，提升项目的代码质量、安全性和可维护性。

**日期**: 2026-05-15

---

## 🎯 修复问题清单

### 🔴 高优先级问题

#### 1. API密钥硬编码泄露
**问题描述**: API密钥直接硬编码在代码中，存在严重安全风险
**影响文件**: 
- [app_flet.py](file:///c:\Users\cattei\Documents\ZMT众盟\software\app_flet.py#L19)
- [detailed_diagnosis.py](file:///c:\Users\cattei\Documents\ZMT众盟\software\detailed_diagnosis.py#L23)

**修复方案**:
- 创建 `config.py` 配置文件
- 使用 `python-dotenv` 从环境变量加载配置
- 创建 `.env.example` 模板文件
- 更新 `.gitignore` 忽略 `.env` 文件

#### 2. 线程安全问题
**问题描述**: 在非主线程中直接更新UI控件，可能导致界面卡顿或崩溃
**影响文件**: [app_flet.py](file:///c:\Users\cattei\Documents\ZMT众盟\software\app_flet.py)

**修复方案**:
- 使用 `page.run_task()` 在主线程执行UI更新
- 或使用队列机制传递UI更新任务
- 重构 `_add_log`、`_update_progress` 等方法

#### 3. 异常处理过于宽泛
**问题描述**: 使用裸 `except:` 捕获所有异常，缺少具体类型和日志
**影响文件**: [app_flet.py](file:///c:\Users\cattei\Documents\ZMT众盟\software\app_flet.py#L390-L393)

**修复方案**:
- 替换为具体异常类型（`zipfile.BadZipFile`、`IOError`等）
- 添加异常日志记录
- 保留必要的错误信息

---

### 🟡 中优先级问题

#### 4. 未使用的导入
**问题描述**: 部分导入模块未被使用，增加代码冗余
**影响文件**: [app_flet.py](file:///c:\Users\cattei\Documents\ZMT众盟\software\app_flet.py)

**修复方案**:
- 移除 `hashlib`（实际已使用，保留）
- 移除 `queue`（未使用）
- 验证其他导入的必要性

#### 5. 缺少输入验证
**问题描述**: 目录选择后缺少存在性和权限验证
**影响文件**: [app_flet.py](file:///c:\Users\cattei\Documents\ZMT众盟\software\app_flet.py)

**修复方案**:
- 在 `_select_source` 和 `_select_target` 中添加验证
- 检查目录是否存在
- 检查读写权限
- 提供友好的错误提示

#### 6. 重复代码
**问题描述**: 路径缩短显示逻辑重复
**影响文件**: [app_flet.py](file:///c:\Users\cattei\Documents\ZMT众盟\software\app_flet.py)

**修复方案**:
- 抽取 `_shorten_path` 公共方法
- 统一路径显示逻辑

#### 7. 缺少配置管理
**问题描述**: 配置项硬编码在代码中
**影响文件**: [app_flet.py](file:///c:\Users\cattei\Documents\ZMT众盟\software\app_flet.py)

**修复方案**:
- 创建 `config.py` 统一管理所有配置
- 包括API配置、扩展名列表、UI常量等

---

### 🟢 低优先级问题

#### 8. 测试文件位置不符合规范
**问题描述**: 测试文件放在根目录，而非 `test` 目录
**影响文件**: 
- test_conversion_diagnosis.py
- test_fix.py
- test_full.py
- detailed_diagnosis.py

**修复方案**:
- 创建 `test` 目录（如不存在）
- 移动测试文件到 `test` 目录
- 更新相关导入路径

#### 9. 缺少类型注解
**问题描述**: 部分方法缺少完整类型提示
**影响文件**: [app_flet.py](file:///c:\Users\cattei\Documents\ZMT众盟\software\app_flet.py)

**修复方案**:
- 为所有方法添加完整类型注解
- 使用 `typing` 模块的类型

#### 10. 魔法数字
**问题描述**: 硬编码数字缺少语义说明
**影响文件**: [app_flet.py](file:///c:\Users\cattei\Documents\ZMT众盟\software\app_flet.py)

**修复方案**:
- 定义常量替代魔法数字
- 在 `config.py` 中统一管理

---

## 📁 文件修改清单

### 新增文件
1. `config.py` - 配置管理模块
2. `.env.example` - 环境变量模板
3. `requirements.txt` - 依赖清单（如不存在）

### 修改文件
1. `app_flet.py` - 主程序文件（主要修改）
2. `.gitignore` - 添加 `.env` 忽略规则
3. `detailed_diagnosis.py` - 移除硬编码密钥

### 移动文件
1. `test_conversion_diagnosis.py` → `test/`
2. `test_fix.py` → `test/`
3. `test_full.py` → `test/`
4. `detailed_diagnosis.py` → `test/`

---

## 🔧 实施步骤

### 阶段一：配置管理（高优先级）
1. 创建 `config.py`
2. 创建 `.env.example`
3. 更新 `.gitignore`
4. 修改 `app_flet.py` 使用配置文件
5. 修改测试文件使用配置

### 阶段二：线程安全（高优先级）
1. 重构UI更新方法
2. 使用 `page.run_task()` 确保线程安全
3. 测试界面响应性

### 阶段三：异常处理（高优先级）
1. 替换裸 `except` 为具体异常
2. 添加异常日志
3. 测试错误场景

### 阶段四：代码清理（中优先级）
1. 移除未使用导入
2. 抽取重复代码
3. 添加输入验证
4. 替换魔法数字为常量

### 阶段五：项目整理（低优先级）
1. 创建 `test` 目录
2. 移动测试文件
3. 更新导入路径

---

## ⚠️ 风险与注意事项

### 风险1: API密钥变更
- **风险**: 现有用户的exe文件中的密钥会失效
- **缓解**: 
  - 保留向后兼容（优先从环境变量加载，降级到硬编码）
  - 在README中说明配置方法

### 风险2: 线程安全修改可能引入新bug
- **风险**: UI更新逻辑改变可能导致显示异常
- **缓解**: 
  - 逐步修改，每个步骤都测试
  - 保持现有功能行为不变

### 风险3: 测试文件移动影响现有测试
- **风险**: 测试脚本路径改变可能导致测试失败
- **缓解**: 
  - 更新所有相关导入
  - 测试移动后的脚本是否正常运行

---

## ✅ 验收标准

1. **安全性**: API密钥不再硬编码在提交的代码中
2. **稳定性**: 长时间运行转换任务不会崩溃
3. **可维护性**: 代码结构清晰，配置统一管理
4. **完整性**: 所有原有功能保持正常工作
5. **规范性**: 测试文件位于正确目录

---

## 📝 后续优化建议（可选）

1. 添加单元测试覆盖核心逻辑
2. 使用日志模块替代print
3. 添加进度断点恢复功能
4. 支持转换队列管理
5. 添加暗黑模式切换
