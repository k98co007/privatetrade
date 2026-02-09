/**
 * Python Worker Wrapper - Node.js에서 Python 백테스팅 엔진 호출
 * 역할: Child Process 관리, JSON 입/출 변환, 타임아웃 처리
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');

class PythonWorker {
  constructor(pythonPath = 'python3') {
    this.pythonPath = pythonPath;
    this.workerPath = path.join(__dirname, '..', '..', 'py_backtest', 'worker.py');
    this.process = null;
    this.requestQueue = [];
    this.timeoutMs = 30000; // 30초 타임아웃
  }

  /**
   * Python Worker 프로세스 시작
   */
  start() {
    return new Promise((resolve, reject) => {
      try {
        this.process = spawn(this.pythonPath, [this.workerPath], {
          stdio: ['pipe', 'pipe', 'pipe'],
          cwd: path.dirname(this.workerPath)
        });

        // 표준 출력 수신 (결과)
        this.process.stdout.on('data', (data) => {
          this._handleOutput(data.toString());
        });

        // 표준 에러 수신 (로깅)
        this.process.stderr.on('data', (data) => {
          console.error(`[Python Worker] ${data.toString()}`);
        });

        // 프로세스 종료
        this.process.on('close', (code) => {
          console.log(`Python Worker exited with code ${code}`);
          this.process = null;
        });

        // 프로세스 에러
        this.process.on('error', (err) => {
          console.error(`Failed to start Python Worker: ${err}`);
          reject(err);
        });

        console.log('[PythonWorker] Started successfully');
        resolve();
      } catch (err) {
        reject(err);
      }
    });
  }

  /**
   * 백테스팅 요청 실행
   * 
   * @param {Object} config - {
   *   stock_code: "005930",
   *   strategy: {...},
   *   prices: {...},
   *   initial_capital: 10000000
   * }
   * @param {number} timeout - 타임아웃 (ms)
   * @return {Promise<Object>} 백테스팅 결과
   */
  async execute(config, timeout = null) {
    if (!this.process) {
      throw new Error('Python Worker is not running');
    }

    return new Promise((resolve, reject) => {
      const requestId = Date.now().toString(36) + Math.random().toString(36);
      const timeoutMs = timeout || this.timeoutMs;

      // 타임아웃 처리
      const timer = setTimeout(() => {
        this._removeRequest(requestId);
        reject(new Error(`Backtest timeout after ${timeoutMs}ms for ${config.stock_code}`));
      }, timeoutMs);

      // 요청 등록
      const request = {
        id: requestId,
        config: config,
        timer: timer,
        resolve: resolve,
        reject: reject
      };
      this.requestQueue.push(request);

      // JSON 요청 전송
      try {
        const jsonRequest = JSON.stringify(config) + '\n';
        this.process.stdin.write(jsonRequest);
      } catch (err) {
        clearTimeout(timer);
        this._removeRequest(requestId);
        reject(new Error(`Failed to send request: ${err.message}`));
      }
    });
  }

  /**
   * Python 출력 처리
   * @private
   */
  _handleOutput(output) {
    const lines = output.trim().split('\n');

    for (const line of lines) {
      if (!line.trim()) continue;

      try {
        const response = JSON.parse(line);

        if (response.status === 'success') {
          // 성공 응답
          const request = this.requestQueue.shift();
          if (request) {
            clearTimeout(request.timer);
            request.resolve(response.data);
          }
        } else if (response.status === 'error') {
          // 에러 응답
          const request = this.requestQueue.shift();
          if (request) {
            clearTimeout(request.timer);
            request.reject(new Error(response.error));
          }
        }
      } catch (err) {
        console.error(`Failed to parse Python response: ${line}`);
      }
    }
  }

  /**
   * 요청 제거
   * @private
   */
  _removeRequest(requestId) {
    const idx = this.requestQueue.findIndex(r => r.id === requestId);
    if (idx !== -1) {
      this.requestQueue.splice(idx, 1);
    }
  }

  /**
   * Worker 종료
   */
  stop() {
    if (this.process) {
      this.process.kill();
      this.process = null;
    }
  }
}

// Singleton 인스턴스
let workerInstance = null;

/**
 * PythonWorker 싱글톤 생성/획득
 */
async function getPythonWorker() {
  if (!workerInstance) {
    workerInstance = new PythonWorker();
    await workerInstance.start();
  }
  return workerInstance;
}

/**
 * 백테스팅 실행 (상위 인터페이스)
 * 
 * @param {Object} config - 백테스팅 설정
 * @return {Promise<Object>} 백테스팅 결과
 */
async function runBacktest(config) {
  const worker = await getPythonWorker();
  return worker.execute(config);
}

/**
 * Worker 종료
 */
function closePythonWorker() {
  if (workerInstance) {
    workerInstance.stop();
    workerInstance = null;
  }
}

module.exports = {
  PythonWorker,
  getPythonWorker,
  runBacktest,
  closePythonWorker
};
