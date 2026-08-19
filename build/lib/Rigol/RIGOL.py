import pyvisa
import time
import logging


class RigolInstrument:
    def __init__(self, resource_name, verbose=1):
        self.verbose = verbose
        self.inst = pyvisa.ResourceManager("@py").open_resource(resource_name)
        self.inst.timeout = 5000
        self.inst.encoding = 'utf-8'
        self.idn = self.get_idn()
        self.instrument_type = self.classify_instrument()

    def get_idn(self):
        try:
            self.inst.write('*IDN?')
            time.sleep(0.1)
            return self.inst.read().strip()
        except pyvisa.errors.VisaIOError:
            if self.verbose >= 2:
                print(f"  ✗ IDN query failed:")
            return "Unknown"

    def getter_idn(self):
        return self.idn

    def classify_instrument(self):
        idn_upper = self.idn.upper()
        if "RIGOL" in idn_upper and "DG" in idn_upper:
            return "generator"
        elif "RIGOL" in idn_upper and ("DS" in idn_upper or "MSO" in idn_upper):
            return "oscilloscope"
        else:
            return "unknown"

    def write(self, command):
        self.inst.write(command)

    def query(self, command):
        return self.inst.query(command)
        
    def read(self):
        return self.inst.read()

    def close(self):
        self.inst.close()
        time.sleep(2)
    
    def __str__(self):
        return f"{self.instrument_type.capitalize()} - IDN: {self.idn}"


    def generate_waveform(self, channel, waveform_type, frequency, amplitude, offset=0, phase=0, duty_cycle=50):
        """Note that writing to CH1 is different from writing to CH2...."""
        args = f"{frequency}, {amplitude}, {offset} "
        
        if channel == "CH1":
            # print(channel)
            self.write('VOLT:UNIT VPP')
            time.sleep(0.05)
            self.write(f'APPL:{waveform_type} {args}')   # e.g. APPL:RAMP 1000, 2.5, 0.5
            time.sleep(0.05)
            self.write(f'PHAS {phase} ')
            time.sleep(0.05)
            self.write("OUTP1 ON")
            # self.toggle("CH1", "ON", self)

        else:
            # for CH2 use the CH-specific notation...
            self.write(f'VOLT:UNIT:{channel} VPP')
            time.sleep(0.05)
            self.write(f'APPL:{waveform_type}:{channel} {args}')  # e.g. APPL:SQUare:CH2 1000, 2.5, 0.5
            time.sleep(0.05)
            self.write(f'PHAS:{channel} {phase} ')
            time.sleep(0.05)
            self.write('OUTP:CH2 ON ')
            # self.toggle(f"CH2", "ON", self)

# =========================================

def detect_rigol_instruments(verbose=1):
    """
    Retourne un tuple (generator, oscilloscope) si présents, sinon None.
    
    Verbose : 0 = silent, 1 = normal, 2 = debug
    
    """
    rm = pyvisa.ResourceManager("@py")
    devices = [d for d in rm.list_resources() if "USB" in d]

    # prints
    if verbose >=2:
        print(f"Devices : {devices}")

    generator = None
    oscilloscope = None
    if verbose >=1: print("Detecting...")

    for dev in devices:
        rigol = RigolInstrument(dev)
        if rigol.instrument_type == "generator":
            generator = rigol
            if verbose >=2: print(f"Detected Generator: {generator}")
            if verbose == 1: print(f"Generator Detected.")

        elif rigol.instrument_type == "oscilloscope":
            oscilloscope = rigol
            if verbose >=2: print(f"Detected Oscilloscope: {oscilloscope}")
            if verbose == 1: print(f"Oscilloscope Detected.")
    return generator, oscilloscope


# generator, oscilloscope = detect_rigol_instruments(verbose=2)

# if generator:
#     generator.close()
# else:
#     print("No generator detected.")

# if oscilloscope:
#     oscilloscope.close()
# else:
#     print("No oscilloscope detected.")

