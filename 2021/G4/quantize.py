from Compression import Compression
import sounddevice as sd
import numpy as np
import psutil
import time
import zlib


# Accumulated percentage of used CPU. 
CPU_total = 0

# Number of samples of the CPU usage.
CPU_samples = 0

# CPU usage average.
CPU_average = 0

class BR_Control(Compression):
    
    QUANTIZER_STEP = 2
    
    def init(self, args):
        Compression.init(self, args)
        self.quantizer_step = args.quantizer_step
    def deadzone_quantizer(self,x):
        for i in x:
            i = (i / self.quantizer_step).astype(np.int16)
        return x
    def deadzone_dequantizer(self,x):
        for i in x:
            i = self.quantizer_step * i
        return x
    def pack(self,chunk):
        cchunk = self.deadzone_quantizer(chunk)

        cchunk = np.array(self.recorded_chunk_number,dtype='>H').tobytes() + cchunk.tobytes()

        cchunk = super().pack(cchunk)
        return cchunk
    def unpack(self,chunk):
        message = super().unpack(chunk)

        (chunk_number,) = np.frombuffer(message[:2],dtype='>H')
        chunk = np.frombuffer(message[2:], np.int16).reshape(self.frames_per_chunk, self.number_of_channels)

        uchunk = self.deadzone_dequantizer(chunk)
        return uchunk,chunk_number
    def receive_and_buffer(self):
        message = super().receive()
        #Desempacamos el mensaje
        (chunk,chunk_number) = self.unpack(message)
        self._buffer[chunk_number % self.cells_in_buffer] = chunk
        return chunk_number
    def record_send_and_play(self, indata, outdata, frames, time, status):
        self.recorded_chunk_number = (self.recorded_chunk_number + 1) % self.CHUNK_NUMBERS
        #Metemos el mensaje y el numero de chunk en el mismo paquete
        #Codificamos los primeros 2 bytes correspondientes a 
        #el numero de chunk
        chunk = self.pack(indata)
        #enviamos el paquete
        super().send_chunk(chunk)
        super().play_chunk(outdata)
    def run(self):
         # Buffer creation.
        self._buffer = [None] * self.cells_in_buffer
        for i in range(self.cells_in_buffer):
            self._buffer[i] = self.empty_chunk

        # Chunks counters.
        self.recorded_chunk_number = 0
        self.played_chunk_number = 0

        print("Compression: press <CTRL> + <c> to quit")
        print("Compression: buffering ... ")

        with sd.Stream(samplerate=self.frames_per_second, blocksize=self.frames_per_chunk, dtype=self.sample_type, channels=self.number_of_channels, callback=self.record_send_and_play):
            first_received_chunk_number = self.receive_and_buffer()
            self.played_chunk_number = (first_received_chunk_number - self.chunks_to_buffer) % self.cells_in_buffer
            while True:
                self.receive_and_buffer()

    # Shows CPU usage.
    def print_feedback_message(self):
        # Be careful, variables updated only in the subprocess.
        global CPU_total
        global CPU_samples
        global CPU_average
        CPU_usage = psutil.cpu_percent()
        CPU_total += CPU_usage
        CPU_samples += 1
        CPU_average = CPU_total/CPU_samples
        print(f"{int(CPU_usage)}/{int(CPU_average)}", flush=True, end=' ')

    # This method runs in a different process to the intercom, and its
    # only task is to print the feedback messages with the CPU load,
    # waiting for the interrupt signal generated by the user (CTRL+C).
    def feedback(self):
        global CPU_average
        try:
            while True:
                self.print_feedback_message()
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n Quantizer: average CPU usage = {CPU_average} %")

    def add_args(self):
        parser = Compression.add_args(self)
        parser.add_argument("-qs", "--quantizer_step",
                            help="Quantizer step in deadzone quantization.",
                            type=int, default=BR_Control.QUANTIZER_STEP)
        return parser

if __name__ == "__main__":
    intercom = BR_Control()
    parser = intercom.add_args()
    args = parser.parse_args()
    intercom.init(args)
    try:
        intercom.run()
    except KeyboardInterrupt:
        print("Quantizer: goodbye 2020¯\_(ツ)_/¯")
