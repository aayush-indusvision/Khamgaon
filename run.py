import sys
import multiprocessing
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel
from analytics_cam_1_0904 import *
from analytics_cam_2_0904 import *
from dashboard import *
import time

dash_downtime = Dashboard_downtime(url='http://localhost:8011/api/downtime-analysis/')


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Control")
        self.setGeometry(100, 100, 400, 200)

        # Initialize layout
        self.layout = QVBoxLayout()
        
        # Add a label to display the status
        self.status_label = QLabel("Status: Idle", self)
        self.layout.addWidget(self.status_label)

        # Add buttons for starting and stopping the process
        self.start_button = QPushButton("Start Process", self)
        self.stop_button = QPushButton("Stop Process", self)

        # Set initial state for the stop button (disabled initially)
        self.stop_button.setEnabled(False)

        # Add buttons to layout
        self.layout.addWidget(self.start_button)
        self.layout.addWidget(self.stop_button)

        # Connect buttons to functions
        self.start_button.clicked.connect(self.start_process)
        self.stop_button.clicked.connect(self.stop_process)

        # Set layout for the window
        self.setLayout(self.layout)

        self.process1 = None
        self.process2 = None

    def start_process(self):
        # Create separate queues for each function
        queue1 = multiprocessing.Queue()
        queue2 = multiprocessing.Queue()

        # Create two processes
        self.process1 = multiprocessing.Process(target=run_main_1, args=(queue1,))
        self.process2 = multiprocessing.Process(target=run_main_2, args=(queue2,))

        # Start the processes
        self.process1.start()
        self.process2.start()

        # Update GUI status
        self.status_label.setText("Status: Running")
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    def stop_process(self):
        if self.process1 and self.process2:
            # Terminate the processes gracefully
            self.process1.terminate()
            self.process2.terminate()
            self.process1.join()
            self.process2.join()

            # Update GUI status
            self.status_label.setText("Status: Stopped")
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)


def run_main_1(queue):
    while True:
        main_1(queue)


def run_main_2(queue):
    while True:
        main_2(queue)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
