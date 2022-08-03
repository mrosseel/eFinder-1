from machine import Pin,SPI
import framebuf
import time
import sys
import select

DC = 8
RST = 12
MOSI = 11
SCK = 10
CS = 9
ln = ["ScopeDog eFinder","","No eFinder yet"]

class OLED_2inch23(framebuf.FrameBuffer):
    def __init__(self):
        self.width = 128
        self.height = 32
        
        self.cs = Pin(CS,Pin.OUT)
        self.rst = Pin(RST,Pin.OUT)
        
        self.cs(1)
        self.spi = SPI(1)
        self.spi = SPI(1,1000_000)
        self.spi = SPI(1,10000_000,polarity=0, phase=0,sck=Pin(SCK),mosi=Pin(MOSI),miso=None)
        self.dc = Pin(DC,Pin.OUT)
        self.dc(1)
        self.buffer = bytearray(self.height * self.width // 8)
        super().__init__(self.buffer, self.width, self.height, framebuf.MONO_VLSB)
        self.init_display()
        
        self.white =   0xffff
        self.balck =   0x0000
        
    def write_cmd(self, cmd):
        self.cs(1)
        self.dc(0)
        self.cs(0)
        self.spi.write(bytearray([cmd]))
        self.cs(1)

    def write_data(self, buf):
        self.cs(1)
        self.dc(1)
        self.cs(0)
        self.spi.write(bytearray([buf]))
        self.cs(1)

    def init_display(self):
        self.rst(1)
        time.sleep(0.001)
        self.rst(0)
        time.sleep(0.01)
        self.rst(1)
        self.write_cmd(0xAE)#turn off OLED display*/
        self.write_cmd(0x04)#turn off OLED display*/
        self.write_cmd(0x10)#turn off OLED display*/	
        self.write_cmd(0x40)#set lower column address*/ 
        self.write_cmd(0x81)#set higher column address*/ 
        self.write_cmd(0x80)#--set start line address  Set Mapping RAM Display Start Line (0x00~0x3F, SSD1305_CMD)
        self.write_cmd(0xA1)#--set contrast control register
        self.write_cmd(0xFF)# Set SEG Output Current Brightness 
        self.write_cmd(0xA8)#--Set SEG/Column Mapping	
        self.write_cmd(0x1F)#Set COM/Row Scan Direction   
        self.write_cmd(0xC8)#--set normal display  
        self.write_cmd(0xD3)#--set multiplex ratio(1 to 64)
        self.write_cmd(0x00)#--1/64 duty
        self.write_cmd(0xD5)#-set display offset	Shift Mapping RAM Counter (0x00~0x3F) 
        self.write_cmd(0xF0)#-not offset
        self.write_cmd(0xD8) #--set display clock divide ratio/oscillator frequency
        self.write_cmd(0x05)#--set divide ratio, Set Clock as 100 Frames/Sec
        self.write_cmd(0xD9)#--set pre-charge period
        self.write_cmd(0xC2)#Set Pre-Charge as 15 Clocks & Discharge as 1 Clock
        self.write_cmd(0xDA) #--set com pins hardware configuration 
        self.write_cmd(0x12)   
        self.write_cmd(0xDB) #set vcomh
        self.write_cmd(0x08)#Set VCOM Deselect Level
        self.write_cmd(0xAF); #-Set Page Addressing Mode (0x00/0x01/0x02)

    def show(self):
        for page in range(0,4):
            self.write_cmd(0xb0 + page)
            self.write_cmd(0x04)
            self.write_cmd(0x10)
            self.dc(1)
            for num in range(0,128):
                self.write_data(self.buffer[page*128+num])

def send_pin(p):
    n=0
    for n in range(5):
        if p.value()== True: 
            return
    time.sleep(0.3)
    if p.value()==True:
        print(str(p)[4:6])
    elif str(p)[4:6]=='21':
        print("20\n")
    time.sleep(0.1)
    
          
if __name__=='__main__':

    OLED = OLED_2inch23()
    OLED.fill(0x0000) 
    OLED.text(ln[0],1,1,OLED.white)
    OLED.text(ln[1],1,12,OLED.white)
    OLED.text(ln[2],1,23,OLED.white)
    OLED.show()
    left = Pin(16,Pin.IN,Pin.PULL_UP)
    up = Pin(17,Pin.IN,Pin.PULL_UP)
    right = Pin(18,Pin.IN,Pin.PULL_UP)
    down = Pin(19,Pin.IN,Pin.PULL_UP)
    select_button = Pin(21,Pin.IN,Pin.PULL_UP)
    left.irq(trigger=Pin.IRQ_FALLING, handler=send_pin)
    up.irq(trigger=Pin.IRQ_FALLING, handler=send_pin)
    right.irq(trigger=Pin.IRQ_FALLING, handler=send_pin)
    down.irq(trigger=Pin.IRQ_FALLING, handler=send_pin)
    select_button.irq(trigger=Pin.IRQ_FALLING, handler=send_pin)
    count =0
    while True:
        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            ch = sys.stdin.readline().strip('\n')
            y = int(ch[0:1])
            ln[y] = ch[2:]
            OLED.fill(0x0000) 
            #OLED.show()
            OLED.text(ln[0],1,1,OLED.white)
            OLED.text(ln[1],1,12,OLED.white)
            OLED.text(ln[2],1,23,OLED.white)
            OLED.show()
