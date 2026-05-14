package main

import (
	"bufio"
	"context"
	_ "embed"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	goruntime "runtime"
	"strings"
	"sync"
	"syscall"

	"github.com/wailsapp/wails/v2/pkg/runtime"
)

//go:embed markitdown_bridge.exe
var bridgeExe []byte

const (
	builtinAPIKey  = "sk-duohvgsidlebysltfcbozhhdfmririmmxalakbzdqwikxaqhq"
	builtinModel   = "deepseek-ai/DeepSeek-OCR"
	builtinBaseURL = "https://api.siliconflow.cn/v1"
)

type App struct {
	ctx context.Context
}

func NewApp() *App {
	return &App{}
}

func (a *App) startup(ctx context.Context) {
	a.ctx = ctx
}

func (a *App) SelectDirectory() string {
	dir, err := runtime.OpenDirectoryDialog(a.ctx, runtime.OpenDialogOptions{
		Title: "选择目录",
	})
	if err != nil || dir == "" {
		return ""
	}
	return dir
}

func (a *App) StartConvert(sourceDir, targetDir string) error {
	if sourceDir == "" || targetDir == "" {
		return fmt.Errorf("源目录和目标目录不能为空")
	}

	go func() {
		err := runConversion(sourceDir, targetDir, func(line string) {
			runtime.EventsEmit(a.ctx, "log", line)

			if strings.HasPrefix(line, "PROGRESS:") {
				var current, total int
				fmt.Sscanf(line, "PROGRESS:%d/%d", &current, &total)
				runtime.EventsEmit(a.ctx, "progress", map[string]int{
					"current": current,
					"total":   total,
				})
			}

			if strings.HasPrefix(line, "DONE:") {
				runtime.EventsEmit(a.ctx, "done", line)
			}
		})

		if err != nil {
			runtime.EventsEmit(a.ctx, "error", err.Error())
		}
	}()

	return nil
}

func runConversion(sourceDir, targetDir string, onLog func(string)) error {
	onLog("🔍 正在准备独立转换环境...")

	// 把嵌入的 bridge exe 写入临时目录
	bridgePath, err := writeBridgeExe()
	if err != nil {
		return fmt.Errorf("无法准备转换工具: %v", err)
	}
	defer os.Remove(bridgePath)

	onLog(fmt.Sprintf("📜 转换工具已就绪: %s", bridgePath))

	args := []string{
		"--source", sourceDir,
		"--target", targetDir,
		"--api-key", builtinAPIKey,
		"--model", builtinModel,
		"--base-url", builtinBaseURL,
	}

	cmd := exec.Command(bridgePath, args...)
	cmd.Env = os.Environ()

	if goruntime.GOOS == "windows" {
		cmd.SysProcAttr = &syscall.SysProcAttr{
			HideWindow: true,
		}
	}

	stdoutPipe, err := cmd.StdoutPipe()
	if err != nil {
		return fmt.Errorf("创建管道失败: %v", err)
	}

	stderrPipe, err := cmd.StderrPipe()
	if err != nil {
		return fmt.Errorf("创建 stderr 管道失败: %v", err)
	}

	if err := cmd.Start(); err != nil {
		return fmt.Errorf("启动转换进程失败: %v", err)
	}

	var wg sync.WaitGroup
	wg.Add(2)

	go func() {
		defer wg.Done()
		scanner := bufio.NewScanner(stdoutPipe)
		scanner.Buffer(make([]byte, 1024*1024), 1024*1024)
		for scanner.Scan() {
			onLog(scanner.Text())
		}
	}()

	go func() {
		defer wg.Done()
		scanner := bufio.NewScanner(stderrPipe)
		scanner.Buffer(make([]byte, 1024*1024), 1024*1024)
		for scanner.Scan() {
			onLog(fmt.Sprintf("[STDERR] %s", scanner.Text()))
		}
	}()

	wg.Wait()

	if err := cmd.Wait(); err != nil {
		return fmt.Errorf("转换进程异常退出: %v", err)
	}

	return nil
}

func writeBridgeExe() (string, error) {
	tmpDir := os.TempDir()
	if goruntime.GOOS == "windows" {
		tmpDir = os.Getenv("TEMP")
		if tmpDir == "" {
			tmpDir = os.TempDir()
		}
	}

	exePath := filepath.Join(tmpDir, fmt.Sprintf("markitdown_bridge_%d.exe", os.Getpid()))

	f, err := os.Create(exePath)
	if err != nil {
		return "", fmt.Errorf("创建临时文件失败: %v", err)
	}
	defer f.Close()

	if _, err := f.Write(bridgeExe); err != nil {
		os.Remove(exePath)
		return "", fmt.Errorf("写入工具文件失败: %v", err)
	}

	return exePath, nil
}
