#!/usr/bin/python3

# Program to implement an eFinder (electronic finder) on motorised Alt Az telescopes
# Copyright (C) 2022 Keith Venables.
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# This variant is customised for ZWO ASI ccds as camera, Nexus DSC as telescope interface
# and ScopeDog or ServoCat as the telescope drive system.
# Optional is an Adafruit 2x16 line LCD with integrated buttons
# It requires astrometry.net installed
# It requires Skyfield

import subprocess
import time
import os
import glob
from os import path
import math
import zwoasi as asi
from PIL import Image, ImageTk, ImageDraw, ImageOps
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import Label, Radiobutton, StringVar, Checkbutton, Button, Frame
from shutil import copyfile
import socket
import re
from skyfield.api import load, Star, wgs84
from pathlib import Path
import fitsio
from fitsio import FITS,FITSHDR
  
version = '12_1_wifi'
os.system('pkill -9 -f eFinder.py') # comment out if this is the autoboot program

HOST = '10.0.0.1'
PORT = 4060
home_path = str(Path.home())
try: # remove this section if no LCD  module is to be fitted
    import board
    import busio
    import adafruit_character_lcd.character_lcd_rgb_i2c as character_lcd
    i2c = busio.I2C(board.SCL, board.SDA)
    lcd = character_lcd.Character_LCD_RGB_I2C(i2c, 16, 2)
    lcd.color = [100, 0, 0]
    lcd.clear()
    lcd.message = "eFinder GUI v"+version+"\ncontrol via VNC"
except:
    pass

deltaAz = deltaAlt = 0
scope_x = scope_y = 0
d_x_str = d_y_str = "0"
image_height = 960
image_width = 1280
offset_new = offset_saved = offset = offset_reset = (0,0)
align_count = 0
report = {'N':'Not tracking','T':'Tracking','A':'AltAz mode','P':'EQ Mode','G':'GEM mode','0':'not aligned','1':'1-star aligned   ','2':'2-star aligned   ','3':'3-star aligned   '}
solved = False
box_list = ['','','','','','']
eye_piece =[]
radec = 'no_radec'
offset_flag = False
f_g = 'red'
b_g = 'black'
solved_radec = 0,0
        
def sidereal():
    global LST
    t=ts.now()
    LST = t.gmst+Long/15 #as decimal hours
    LSTstr = str(int(LST))+'h '+str(int((LST*60) % 60))+'m '+str(int((LST*3600) % 60))+'s'
    lbl_LST=Label(window,bg=b_g,fg=f_g,text=LSTstr)
    lbl_LST.place(x=55,y=44)
    lbl_UTC=Label (window,bg=b_g,fg=f_g, text=t.utc_strftime('%H:%M:%S'))
    lbl_UTC.place(x=55, y=22)
    lbl_date=Label (window,bg=b_g,fg=f_g, text=t.utc_strftime('%d %b %Y'))
    lbl_date.place(x=55, y=0)
    window.update()
    time.sleep(0.95)
    lbl_UTC.destroy()
    lbl_LST.destroy()
    lbl_date.destroy()
    lbl_LST.after(10, sidereal)

def convAltaz(ra,dec): # decimal ra in hours, decimal dec.
    Rad = math.pi/180
    ra =ra * 15 # need to work in degrees now
    LSTd = LST * 15
    LHA = (LSTd - ra + 360) - ((int)((LSTd - ra + 360)/360))*360   
    x = math.cos(LHA * Rad) * math.cos(dec * Rad)
    y = math.sin(LHA * Rad) * math.cos(dec * Rad)
    z = math.sin(dec * Rad)    
    xhor = x * math.cos((90 - Lat) * Rad) - z * math.sin((90 - Lat) * Rad)
    yhor = y
    zhor = x * math.sin((90 - Lat) * Rad) + z * math.cos((90 - Lat) * Rad)
    az = math.atan2(yhor, xhor) * (180/math.pi) + 180
    alt = math.asin(zhor) * (180/math.pi)
    return(alt,az)

def dd2dms(dd): # converts Dec or Alt from signed decimal to D:M:S
    is_positive = dd >= 0
    dd = abs(dd)
    minutes,seconds = divmod(dd*3600,60)
    degrees,minutes = divmod(minutes,60)
    sign = '+' if is_positive else '-'  
    dms = '%s%02d:%02d:%02d' % (sign,degrees,minutes,seconds)
    return(dms)

def dd2aligndms(dd): # converts Dec or Alt from signed decimal to D*M:S with '*' as delimter (LX200 protocol)
    is_positive = dd >= 0
    dd = abs(dd)
    minutes,seconds = divmod(dd*3600,60)
    degrees,minutes = divmod(minutes,60)
    sign = '+' if is_positive else '-'  
    dms = '%s%02d*%02d:%02d' % (sign,degrees,minutes,seconds)
    return(dms)

def ddd2dms(dd): # converts Az from decimal to D:M:S
    minutes,seconds = divmod(dd*3600,60)
    degrees,minutes = divmod(minutes,60)
    dms = '%03d:%02d:%02d' % (degrees,minutes,seconds)
    return(dms)

def hh2dms(dd): # converts RA from decimal to D:M:S
    minutes,seconds = divmod(dd*3600,60)
    degrees,minutes = divmod(minutes,60)
    dms = '%02d:%02d:%02d' % (degrees,minutes,seconds)
    return(dms)

def rd2xy(ra,dec): # returns the image x,y pixel corrsponding to a J2000 RA & Dec
    result = subprocess.run(["wcs-rd2xy","-w",home_path+"/Solver/images/capture.wcs","-r",str(ra),"-d",str(dec)],capture_output=True, text=True)
    result = str(result.stdout)
    line = result.split('pixel')[1]
    x,y = re.findall("[-,+]?\d+\.\d+",line)
    return(float(x),float(y))

def xy2rd(x,y): # returns the RA & Dec (J2000) corresponding to an image x,y pixel
    result = subprocess.run(["wcs-xy2rd","-w",home_path+"/Solver/images/capture.wcs","-x",str(x),"-y",str(y)],capture_output=True, text=True)
    result = str(result.stdout)
    line = result.split('RA,Dec')[1]
    ra,dec = re.findall("[-,+]?\d+\.\d+",line)
    return(float(ra),float(dec))

def pixel2dxdy(pix_x,pix_y): # converts an image pixel x,y to a delta x,y in degrees.
    pix_scale = 3.74715 if finder.get() == '1' else 4*3.74715
    deg_x = (float(pix_x) - 640)*pix_scale/3600 # in degrees
    deg_y = (480-float(pix_y))*pix_scale/3600
    dxstr = "{: .1f}".format(float(60*deg_x)) # +ve if finder is left of Polaris
    dystr = "{: .1f}".format(float(60*deg_y)) # +ve if finder is looking below Polaris 
    return(deg_x,deg_y,dxstr,dystr)

def dxdy2pixel(dx,dy): # reverse of above
    pix_scale = 3.74715 if finder.get() == '1' else 4*3.74715
    pix_x = dx*3600/pix_scale + 640
    pix_y = 480 - dy*3600/pix_scale
    dxstr = "{: .1f}".format(float(60*dx)) # +ve if finder is left of Polaris
    dystr = "{: .1f}".format(float(60*dy)) # +ve if finder is looking below Polaris 
    return(pix_x,pix_y,dxstr,dystr)
    
def readNexus():
    global scopeAlt,radec, nexus_altaz, nexus_radec
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST,PORT))
        s.send(b':GR#')
        time.sleep(0.1)
        ra = str(s.recv(16).decode('ascii')).strip('#').split(':')
        s.send(b':GD#')
        time.sleep(0.1)
        dec = re.split(r'[:*]',str(s.recv(16).decode('ascii')).strip('#'))
    radec = ra[0]+ra[1]+dec[0]+dec[1]
    nexus_radec = (float(ra[0]) + float(ra[1])/60 + float(ra[2])/3600),(float(dec[0]) + float(dec[1])/60 + float(dec[2])/3600)
    nexus_altaz = convAltaz(*(nexus_radec))
    #nexus = Star(ra_hours=(float(ra[0]),float(ra[1]),float(ra[2])),dec_degrees=(float(dec[0]),float(dec[1]),float(dec[2])),epoch=ts.now())
    #nexus_Pos=location.at(ts.now()).observe(nexus)
    #ra, dec, d = nexus_Pos.radec()
    scopeAlt = nexus_altaz[0]*math.pi/180
    tk.Label(window,width=10,anchor="e",text=hh2dms(nexus_radec[0]),bg=b_g,fg=f_g).place(x=225,y=804)
    tk.Label(window,width=10,anchor="e",text=dd2dms(nexus_radec[1]),bg=b_g,fg=f_g).place(x=225,y=826)
    tk.Label(window,width=10,anchor="e",text=ddd2dms(nexus_altaz[0]),bg=b_g,fg=f_g).place(x=225,y=870)
    tk.Label(window,width=10,anchor="e",text=dd2dms(nexus_altaz[1]),bg=b_g,fg=f_g).place(x=225,y=892)

def zwoInit():
    global camera, camType
    asi.init("/lib/zwoasi/armv7/libASICamera2.so")
    num_cameras = asi.get_num_cameras()
    if num_cameras == 0:
        camType = "not found"
    else:
        camType = "ZWO"
    camera = asi.Camera(0)
    camera.set_control_value(asi.ASI_BANDWIDTHOVERLOAD, camera.get_controls()['BandWidth']['MinValue'])
    camera.disable_dark_subtract()
    camera.set_control_value(asi.ASI_WB_B, 99)
    camera.set_control_value(asi.ASI_WB_R, 75)
    camera.set_control_value(asi.ASI_GAMMA, 50)
    camera.set_control_value(asi.ASI_BRIGHTNESS, 50)
    camera.set_control_value(asi.ASI_FLIP, 0)
    camera.set_image_type(asi.ASI_IMG_RAW8)

def capture():
    if camType == "not found":
        box_write("camera not found")
        return
    exp = int(1000000 * float(exposure.get()))
    gn = int(float(gain.get()))
    timestr = time.strftime("%Y%m%d-%H%M%S")
    camera = asi.Camera(0)
    camera.set_control_value(asi.ASI_GAIN, gn)
    camera.set_control_value(asi.ASI_EXPOSURE, exp)#microseconds "change to expTime * 1000000"   
    if test.get() == '1':
        copyfile(home_path+'/Solver/test.jpg',home_path+'/Solver/images/capture.jpg')
    elif polaris.get() == '1':
        copyfile(home_path+'/Solver/polaris.jpg',home_path+'/Solver/images/capture.jpg')
    else:
        camera.capture(filename=home_path+'/Solver/images/capture.jpg')
        copyfile(home_path+'/Solver/images/capture.jpg',home_path+'/Solver/Stills/'+timestr+'_'+radec+'.jpg')
    image_show()
    
def solveImage():
    global solved, scopeAlt, star_name, star_name_offset,solved_radec,solved_altaz
    scale = 3.75 if finder.get() == '1' else 4*3.75
    box_write('"/pixel: '+str(scale))
    scale_low = str(scale * 0.9)
    scale_high = str(scale * 1.1)
    name_that_star = ([]) if (offset_flag == True) else (["--no-plots"])
    limitOptions = 		(["--overwrite", 	# overwrite any existing files
                            "--skip-solved", 	# skip any files we've already solved
                            "--cpulimit","10"	# limit to 10 seconds(!). We use a fast timeout here because this code is supposed to be fast
                            ]) 
    optimizedOptions = 	(["--downsample","2",	# downsample 4x. 2 = faster by about 1.0 second; 4 = faster by 1.3 seconds
                            "--no-remove-lines",	# Saves ~1.25 sec. Don't bother trying to remove surious lines from the image
                            "--uniformize","0"	# Saves ~1.25 sec. Just process the image as-is
                            ])
    scaleOptions = 		(["--scale-units","arcsecperpix",	# next two params are in arcsecs. Supplying this saves ~0.5 sec
                            "--scale-low",scale_low,			# See config above
                            "--scale-high",scale_high,			# See config above
                            ])
    fileOptions = 		(["--new-fits","none",	# Don't create a new fits
                            "--solved","none",	# Don't generate the solved output
                            "--rdls","none",		# Don't generate the point list
                            "--match","none",		# Don't generate matched output
                            "--corr","none",		# Don't generate .corr files
                            ])
    #"--temp-axy" We can't specify not to create the axy list, but we can write it to /tmp
    cmd = ["solve-field"]
    captureFile = home_path+"/Solver/images/capture.jpg"
    options = limitOptions + optimizedOptions + scaleOptions + fileOptions + [captureFile]
    start_time=time.time()
    result = subprocess.run(cmd + name_that_star +  options, capture_output=True, text=True)
    elapsed_time = time.time() - start_time
    #print (result.stdout)
    elapsed_time = 'elapsed time '+str(elapsed_time)[0:4]+' sec' 
    tk.Label(window,text=elapsed_time,width = 20,anchor="e",bg=b_g,fg=f_g).place(x=315,y=936)
    result = str(result.stdout)
    if ("solved" not in result):
        box_write('Solve Failed')
        solved = False
        tk.Label(window,width=10,anchor="e",text='no solution',bg=b_g,fg=f_g).place(x=315,y=804)
        tk.Label(window,width=10,anchor="e",text='no solution',bg=b_g,fg=f_g).place(x=315,y=826)
        tk.Label(window,width=10,anchor="e",text='no solution',bg=b_g,fg=f_g).place(x=315,y=870)
        tk.Label(window,width=10,anchor="e",text='no solution',bg=b_g,fg=f_g).place(x=315,y=892)
        tk.Label(window,text=elapsed_time,bg=b_g,fg=f_g).place(x=315,y=936)
        return
    if offset_flag == True:
        table,h= fitsio.read(home_path+'/Solver/images/capture.axy',header=True)
        star_name_offset = table[0][0],table[0][1]
        #print('(capture.axy gives) x,y',table[0][0],table[0][1])
        if "The star" in result:
            lines = result.split('\n')
            for line in lines:
                if (line.startswith("  The star ")):
                    star_name = line.split(' ')[4]
                    print ('Solve-field Plot found: ',star_name)
                    box_write(star_name+' found')
                    break
        else:
            box_write(' no named star')
            print ('No Named Star found')
            star_name = "Unknown"
    solvedPos = applyOffset()
    ra,dec,d = solvedPos.radec(ts.now())
    solved_radec = ra.hours,dec.degrees
    #alt,az,d = solvedPos.apparent().altaz()
    solved_altaz = convAltaz(*(solved_radec))
    scopeAlt = solved_altaz[0]*math.pi/180
    tk.Label(window,width=10,text=hh2dms(solved_radec[0]),anchor="e",bg=b_g,fg=f_g).place(x=315,y=804)
    tk.Label(window,width=10,anchor="e",text=dd2dms(solved_radec[1]),bg=b_g,fg=f_g).place(x=315,y=826)
    tk.Label(window,width=10,anchor="e",text=ddd2dms(solved_altaz[0]),bg=b_g,fg=f_g).place(x=315,y=870)
    tk.Label(window,width=10,anchor="e",text=dd2dms(solved_altaz[1]),bg=b_g,fg=f_g).place(x=315,y=892)
    solved = True
    box_write('solved')
    deltaCalc()
   
def applyOffset(): # creates & returns a 'Skyfield star object' at the set offset and adjusted to Jnow
    x_offset,y_offset,dxstr,dystr = dxdy2pixel(offset[0],offset[1])
    ra,dec = xy2rd(x_offset,y_offset)
    solved = Star(ra_hours=float(ra)/15,dec_degrees=float(dec)) # will set as J2000 as no epoch input
    solvedPos_scope = location.at(ts.now()).observe(solved) # now at Jnow and current location
    return(solvedPos_scope)

def image_show():
    global manual_angle, img3
    img2 = Image.open(home_path+'/Solver/images/capture.jpg')
    width,height = img2.size
    img2 = img2.resize((1014,760),Image.LANCZOS) # original is 1280 x 960
    width,height = img2.size
    scale = 1 if finder.get() == '1' else 4
    h = 60*scale # vertical finder field of view in arc min
    w = 80*scale
    w_offset = width*offset[0]*60/w
    h_offset = height*offset[1]*60/h
    img2 = img2.convert("RGB")
    if grat.get() == '1':
        draw = ImageDraw.Draw(img2)
        draw.line([(width/2,0),(width/2,height)],fill=75,width=2)
        draw.line([(0,height/2),(width,height/2)],fill=75,width=2)
        draw.line([(width/2+w_offset,0),(width/2+w_offset,height)],fill=255,width=1)
        draw.line([(0,height/2-h_offset),(width,height/2-h_offset)],fill=255,width=1)
    if EP.get() == '1':
        draw = ImageDraw.Draw(img2)
        tfov = ((float(EPlength.get())*height/float(param['scope_focal_length']))*60/h)/2 # half tfov in pixels
        draw.ellipse([width/2+w_offset-tfov,height/2-h_offset-tfov,width/2+w_offset+tfov,height/2-h_offset+tfov],fill=None,outline=255,width=1)
    if lock.get()=='1':
        img2 = zoom_at(img2,w_offset,h_offset,1)
    if zoom.get() == '1':
        img2 = zoom_at(img2,0,0,2)
    if flip.get() == '1':
        img2 = ImageOps.flip(img2)
    if mirror.get() == '1':
        img2 = ImageOps.mirror(img2)
    if auto_rotate.get() == '1':
        img2 = img2.rotate(scopeAlt)
    elif manual_rotate.get() == '1':
        angle_deg = angle.get()
        img2 = img2.rotate(float(angle_deg))
    img3=img2
    img2 = ImageTk.PhotoImage(img2)
    panel.configure(image=img2)
    panel.image = img2
    panel.place(x=200,y=5,width=1014,height=760)

def annotate_image():
    global img3
    scale = 3.75 if finder.get() == '1' else 4*3.75
    scale_low = str(scale * 0.9 * 1.2) # * 1.2 is because image has been resized for the display panel
    scale_high = str(scale * 1.1 * 1.2) 
    image_show()
    img3 = img3.save(home_path+"/Solver/images/adjusted.jpg")
    # first need to re-solve the image as it is presented in the GUI, saved as 'adjusted.jpg'
    os.system('solve-field --no-plots --new-fits none --solved none --match none --corr none \
            --rdls none --cpulimit 10 --temp-axy --overwrite --downsample 2 --no-remove-lines --uniformize 0 \
            --scale-units arcsecperpix --scale-low '+scale_low+' \
            --scale-high '+scale_high+' /home/astrokeith/Solver/images/adjusted.jpg')
    # now we can annotate the image adjusted.jpg
    opt1 = " " if bright.get() == '1' else " --no-bright"
    opt2 = " --hipcat=/usr/local/astrometry/annotate_data/hip.fits --hiplabel" if hip.get()=="1" else " "
    opt3 = " --hdcat=/usr/local/astrometry/annotate_data/hd.fits" if hd.get()=='1' else " "
    opt4 = " --abellcat=/usr/local/astrometry/annotate_data/abell-all.fits" if abell.get() == '1' else " "
    opt5 = " --tycho2cat=/usr/local/astrometry/annotate_data/tycho2.kd" if tycho2.get() == '1' else " "
    opt6 = " " if ngc.get() == '1' else " --no-ngc"
    try: # try because the solve may have failed to produce adjusted.jpg
        os.system('python3 /usr/local/astrometry/lib/python/astrometry/plot/plotann.py \
            --no-grid --tcolor="orange" --tsize="14" --no-const'+opt1+opt2+opt3+opt4+opt5+opt6+' \
            /home/astrokeith/Solver/images/adjusted.wcs \
            /home/astrokeith/Solver/images/adjusted.jpg \
            /home/astrokeith/Solver/images/adjusted_out.jpg')
    except:
        pass
    if os.path.exists(home_path+"/Solver/images/adjusted_out.jpg") == True:
        img3 = Image.open(home_path+'/Solver/images/adjusted_out.jpg')
        filelist = glob.glob(home_path+"/Solver/images/adjusted*.*")
        for filePath in filelist:
            try:
                os.remove(filePath)
            except:
                print("problem while deleting file :",filePath)
        box_write('annotation successful')
        img4 = ImageTk.PhotoImage(img3)
        panel.configure(image=img4)
        panel.image = img4
        panel.place(x=200,y=5,width=1014,height=760)
    else:
        box_write('solve failure')
        return

def zoom_at(img, x, y, zoom): # used to crop and shift the image (zoom and offset)
    w, h = img.size
    dh=(h-(h/zoom))/2
    dw=(w-(w/zoom))/2
    img = img.crop((dw +x, dh - y, w-dw+x, h-dh-y))
    return img.resize((w, h), Image.LANCZOS)
    
def deltaCalc():
    global deltaAz,deltaAlt
    deltaAz = solved_altaz[1] - nexus_altaz[1]
    if abs(deltaAz)>180:
        if deltaAz<0:
            deltaAz = deltaAz + 360
        else:
            deltaAz = deltaAz - 360
    deltaAz = 60*(deltaAz*math.cos(scopeAlt)) #actually this is delta'x' in arcminutes
    deltaAlt = solved_altaz[0] - nexus_altaz[0] 
    deltaAlt = 60*(deltaAlt)  # in arcminutes
    deltaAzstr = "{: .1f}".format(float(deltaAz)).ljust(8)[:8]
    deltaAltstr = "{: .1f}".format(float(deltaAlt)).ljust(8)[:8]
    tk.Label(window,width=10,anchor="e",text=deltaAzstr,bg=b_g,fg=f_g).place(x=410,y=870)
    tk.Label(window,width=10,anchor="e",text=deltaAltstr,bg=b_g,fg=f_g).place(x=410,y=892)

def moveScope(dAz,dAlt):
    azPulse = abs(dAz/float(param['azSpeed'])) # seconds
    altPulse = abs(dAlt/float(param['altSpeed']))
    print('%s %.2f  %s  %.2f %s' % ('azPulse:',azPulse,'altPulse:',altPulse,'seconds'))
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST,PORT))
        s.send(b'#:RG#') # set move speed to guide
        box_write('moving scope in Az')
        print('moving scope in Az')
        if dAz > 0: #if +ve move scope left
            s.send(b'#:Me#')
            time.sleep(azPulse)
            s.send(b'#:Q#')
        else:
            s.send(b'#:Mw#')
            time.sleep(azPulse)
            s.send(b'#:Q#')
        time.sleep(0.2)
        box_write('moving scope in Alt')
        print('moving scope in Alt')
        s.send(b'#:RG#')
        if dAlt > 0: #if +ve move scope down
            s.send(b'#:Ms#')
            time.sleep(altPulse)
            s.send(b'#:Q#')
        else:
            s.send(b'#:Mn#')
            time.sleep(altPulse)
            s.send(b'#:Q#')
    box_write('move finished')
    print('move finished')
    time.sleep(1)

def align(): # sends the Nexus the solved RA & Dec (JNow) as an align or sync point. LX200 protocol.
    global align_count
    #readNexus()
    capture()
    solveImage()
    readNexus()
    if solved==False:
        return 
    align_ra = ':Sr'+dd2dms((solved_radec)[0])+'#'
    align_dec = ':Sd'+dd2aligndms((solved_radec)[1])+'#'
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST,PORT))
            s.send(bytes(align_ra.encode('ascii')))
            time.sleep(0.1)
            print('sent align RA command:',align_ra)
            box_write('sent '+align_ra)
            if str(s.recv(1),'ascii') == '0':
                box_write('invalid position')
                tk.Label(window,text="invalid alignment").place(x=20,y=680)
                return
            s.send(bytes(align_dec.encode('ascii')))
            time.sleep(0.1)
            print('sent align Dec command:',align_dec)
            box_write('sent '+align_dec)
            if str(s.recv(1),'ascii') == '0':
                box_write('invalid position')
                tk.Label(window,text="invalid alignment").place(x=20,y=680)               
                return           
            s.send(b':CM#')
            time.sleep(0.1)
            print(':CM#')
            box_write('sent :CM#')
            reply = str(s.recv(20),'ascii')
            print('reply: ',reply)
            s.send(b':GW#')
            time.sleep(0.1)
            p = str(s.recv(4),'ascii')
            print('Align status reply ',p[0:3])
            box_write('Align reply:'+p[0:3])
            align_count +=1
    except Exception as ex:
        print(ex)
        box_write('Nexus error')
    tk.Label(window,text='align count: '+str(align_count),bg=b_g,fg=f_g).place(x=20,y=600)
    tk.Label(window,text='Nexus report: '+p[0:3],bg=b_g,fg=f_g).place(x=20,y=620)
    NexStr = report[p[2]]
    tk.Label(window,text ='Nexus '+NexStr,bg=b_g,fg=f_g).place(x=20,y=466)
    readNexus()
    deltaCalc()

def measure_offset():
    global offset_new, scope_x, scope_y, offset_flag
    offset_flag = True
    readNexus()
    capture()
    solveImage()
    if solved == False:
        box_write('solve failed')
        offset_flag=False
        return
    scope_x,scope_y = star_name_offset
    if star_name == "Unknown": # display warning in red.
        tk.Label(window,width=8,text=star_name,anchor='w',bg=f_g,fg=b_g).place(x=115,y=470)
    else:
        tk.Label(window,width=8,text=star_name,anchor='w',bg=b_g,fg=f_g).place(x=115,y=470)
    box_write(star_name)
    d_x,d_y,dxstr_new,dystr_new = pixel2dxdy(scope_x,scope_y)
    offset_new = d_x,d_y
    tk.Label(window,text=dxstr_new+','+dystr_new+'          ',width=9,anchor='w',bg=b_g,fg=f_g).place(x=110,y=450)
    offset_flag=False
    
def use_new():
    global offset
    offset = offset_new
    x_offset_new,y_offset_new,dxstr,dystr = dxdy2pixel(offset[0],offset[1])
    tk.Label(window,text=dxstr+','+dystr,bg=b_g,fg=f_g,width=8).place(x=870,y=775)

def save_offset():
    global param
    param['d_x'],param['d_y'] = offset
    save_param()
    get_offset()
    box_write('offset saved')

def get_offset():
    x_offset_saved,y_offset_saved,dxstr_saved,dystr_saved = dxdy2pixel(float(param['d_x']),float(param['d_y']))
    tk.Label(window,text=dxstr_saved+','+dystr_saved+'          ',width=9,anchor='w',bg=b_g,fg=f_g).place(x=110,y=520)

def use_loaded_offset():
    global offset
    x_offset_saved,y_offset_saved,dxstr,dystr = dxdy2pixel(float(param['d_x']),float(param['d_y']))
    offset = float(param['d_x']),float(param['d_y'])
    tk.Label(window,text=dxstr+','+dystr,bg=b_g,fg=f_g,width=8).place(x=60,y=400)

def reset_offset():
    global offset
    offset = offset_reset
    box_write('offset reset')
    tk.Label(window,text='0,0',bg=b_g,fg='red',width=8).place(x=60,y=400)

def image():
    readNexus()
    capture()

def solve():
    readNexus()
    solveImage()
    image_show()

def readTarget():
    global target_radec,target_altaz
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s: # read original goto target RA & Dec
        s.connect((HOST,PORT))
        s.send(b':Gr#')
        time.sleep(0.1)
        target_ra = s.recv(16).decode('ascii')
        if target_ra[0:2] == '00' and target_ra[3:5] == '00': # not a valid goto target set yet.
            box_write('no GoTo target')
            return
        s.send(b':Gd#')
        time.sleep(0.1)
        target_dec = s.recv(16).decode('ascii')
        ra = target_ra.strip('#').split(':')

        s.send(b':GD#')
        time.sleep(0.1)
        dec = re.split(r'[:*]',str(s.recv(16).decode('ascii')).strip('#'))
        target_radec = (float(ra[0]) + float(ra[1])/60 + float(ra[2])/3600),(float(dec[0]) + float(dec[1])/60 + float(dec[2])/3600)
        target_altaz = convAltaz(*(target_radec))
        print ('goto RA & Dec',target_ra,target_dec)
        return(target_ra,target_dec)



def goto():
    ra,dec = readTarget()
    align() # local sync scope to true RA & Dec
    if solved == False:
        box_write('solve failed')
        return
    time.sleep(0.2)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s: # send back the original goto target and command a goto
        s.connect((HOST,PORT))
        s.send(bytes((':Sr'+ra).encode('ascii')))
        s.send(bytes((':Sd'+dec).encode('ascii')))
        s.send(b':MS#')
        time.sleep(0.1)
        box_write("moving scope")
        # print(str(s.recv(1),'ascii'))
        # print('GoTo problem')
        # box_write('goto problem')

def move():
    solveImage()
    image_show()
    if solved == False:
        box_write('no solution yet')
        return
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST,PORT))
        s.send(b':Gr#')
        time.sleep(0.1)
        goto_ra = str(s.recv(16).decode('ascii')).strip('#').split(':')
        if goto_ra[0] == '00' and goto_ra[1] == '00': # not a valid goto target set yet.
            box_write('no GoTo target')
            return
        s.send(b':Gd#')
        time.sleep(0.1)
        goto_dec = re.split(r'[:*]',str(s.recv(16).decode('ascii')).strip('#'))
    print ('goto RA & Dec',goto_ra,goto_dec)
    ra = float(goto_ra[0])+float(goto_ra[1])/60+float(goto_ra[2])/3600
    dec = float(goto_dec[0]) + float(goto_dec[1])/60 + float(goto_dec[2])/3600
    print('goto radec',ra,dec)
    alt_g,az_g = convAltaz(ra,dec)
    print('target Az Alt',az_g,alt_g)
    #ra,dec,d = solvedPos.radec(epoch=ts.now())
    #az_s,alt_s = convAltaz(ra.hours,dec.degrees)
    #print('solved Az Alt',az_s,alt_s)
    delta_Az = (az_g - solved_altaz[1])*60 # +ve move scope right
    delta_Alt = (alt_g - solved_altaz[0])*60 # +ve move scope up
    delta_Az_str = "{: .2f}".format(delta_Az)
    delta_Alt_str = "{: .2f}".format(delta_Alt)
    print("deltaAz, deltaAlt:",delta_Az_str,delta_Alt_str)    
    box_write("deltaAz : "+delta_Az_str)
    box_write("deltaAlt: "+delta_Alt_str)
    moveScope(delta_Az,delta_Alt)
    # could insert a new capture and solve?

def on_closing():
    save_param()
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        lcd = character_lcd.Character_LCD_RGB_I2C(i2c, 16, 2)
        lcd.color = [100, 0, 0]
        lcd.clear()
        lcd.message = "eFinder GUI\n by VNC has Quit"
    except:
        pass
    exit()
    
def box_write(new_line):
    t=ts.now()
    for i in range(5,0,-1):
        box_list[i] = box_list[i-1]
    box_list[0] = (t.utc_strftime('%H:%M:%S ') + new_line).ljust(36)[:35]
    for i in range(0,5,1):
        tk.Label(window,text=box_list[i],bg=b_g,fg=f_g).place(x=1050,y=980-i*16)
    
def get_Nexus_geo():
    global location,Long,Lat,NexStr
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST,PORT))
        s.send(b':P#')
        time.sleep(0.1)
        p = str(s.recv(15),'ascii')
        if p[0] == 'L':
            s.send(b':U#')
        s.send(b':P#')
        time.sleep(0.1)
        print ('Connected to Nexus in',str(s.recv(15),'ascii'))
        NexStr = 'connected'
        s.send(b':Gt#')
        time.sleep(0.1)
        Lt = (str(s.recv(7),'ascii'))[0:6].split('*')
        Lat = float(Lt[0]+'.'+Lt[1])
        s.send(b':Gg#')
        time.sleep(0.1)
        Lg = (str(s.recv(8),'ascii'))[0:7].split('*')
        Long = -1*float(Lg[0]+'.'+Lg[1])
        location = earth+wgs84.latlon(Lat,Long)
        s.send(b':GL#')
        local_time = str(s.recv(16),'ascii').strip('#')
        s.send(b':GC#')
        local_date = str(s.recv(16),'ascii').strip('#')
        s.send(b':GG#')
        local_offset = float(str(s.recv(16),'ascii').strip('#'))
        print('Nexus reports: local datetime as',local_date, local_time, ' local offset:',local_offset)
        date_parts = local_date.split('/')
        local_date = date_parts[0]+'/'+date_parts[1]+'/20'+date_parts[2]
        dt_str = local_date+' '+local_time
        format  = "%m/%d/%Y %H:%M:%S"
        local_dt = datetime.strptime(dt_str, format)
        new_dt = str(local_dt + timedelta(hours = local_offset))
        print('Calculated UTC',new_dt)
        print('setting pi clock:')
        os.system('sudo date -u -s "%s"' % new_dt)
        s.send(b':GW#')
        time.sleep(0.1)
        p = str(s.recv(4),'ascii')
        print('Nexus reports',p)

def get_param():
    global eye_piece, param, expRange, gainRange
    if os.path.exists(home_path+"/Solver/eFinder.config") == True:
        with open(home_path+"/Solver/eFinder.config") as h:
            for line in h:
                line=line.strip('\n').split(':')
                param[line[0]] = line[1]
                if (line[0].startswith("Eyepiece")):
                    label,fl,afov = line[1].split(',')
                    eye_piece.append((label,float(fl),float(afov)))
                elif (line[0].startswith("Exp_range")):
                    expRange = line[1].split(',')
                elif (line[0].startswith("Gain_range")):
                    gainRange = line[1].split(',')
                    

def save_param():
    global param
    param['Exposure'] = exposure.get()
    param['Gain'] = gain.get()
    param['Test mode'] = test.get()
    param['200mm finder'] = finder.get()
    with open(home_path+"/Solver/eFinder.config", "w") as h:
        for key, value in param.items():
            h.write('%s:%s\n' % (key,value))

#main code starts here

param = dict()
get_param()

planets = load('de421.bsp')
earth = planets['earth']
ts = load.timescale()
get_Nexus_geo()

zwoInit() # find and initialise a camera

# main program loop, using tkinter GUI
window = tk.Tk()
window.title("ScopeDog eFinder v"+version)
window.geometry('1300x1000+100+40')
window.configure(bg='black')

sidereal()
tk.Label(window,text='Date',fg=f_g,bg=b_g).place(x=15,y=0)
tk.Label(window,text='UTC',bg=b_g,fg=f_g).place(x=15,y=22)
tk.Label(window,text='LST',bg=b_g,fg=f_g).place(x=15,y=44)
tk.Label(window,text='Loc:',bg=b_g,fg=f_g).place(x=15,y=66)
tk.Label(window,width=18,anchor="w",text=str(Long)+'\u00b0  ' + str(Lat)+'\u00b0',bg=b_g,fg=f_g).place(x=55,y=66)
#tk.Label(window,text='Lat:',bg=b_g,fg=f_g).place(x=15,y=88)
#tk.Label(window,width=6,anchor="e",text=str(Lat)+'\u00b0',bg=b_g,fg=f_g).place(x=55,y=88)
img = Image.open(home_path+'/Solver/M16.jpeg')
img = img.resize((1014,760))
img = ImageTk.PhotoImage(img)
panel = tk.Label(window, highlightbackground="red", highlightthickness=2, image=img)
panel.place(x=200,y=5,width=1014,height=760)

exposure = StringVar()
exposure.set(param['Exposure'])
exp_frame = Frame(window,bg='black')
exp_frame.place(x=0,y=100)
tk.Label(exp_frame,text='Exposure',bg=b_g,fg=f_g).pack(padx=1,pady=1)
for i in range(len(expRange)):
    tk.Radiobutton(exp_frame,text=str(expRange[i]),bg=b_g,fg=f_g,width=7,activebackground='red',anchor='w', \
                   highlightbackground='black',value=float(expRange[i]), variable=exposure).pack(padx=1,pady=1)

gain = StringVar()
gain.set(param['Gain'])
gain_frame = Frame(window,bg='black')
gain_frame.place(x=80,y=100)
tk.Label(gain_frame,text='Gain',bg=b_g,fg=f_g).pack(padx=1,pady=1)
for i in range(len(gainRange)):
    tk.Radiobutton(gain_frame,text=str(gainRange[i]),bg=b_g,fg=f_g,width=7,activebackground='red',anchor='w', \
                   highlightbackground='black',value=float(gainRange[i]), variable=gain).pack(padx=1,pady=1)

finder = StringVar()
finder.set(param['200mm finder'])
options_frame = Frame(window,bg='black')
options_frame.place(x=20,y=270)
tk.Checkbutton(options_frame,text='200mm finder',width=13,anchor="w",highlightbackground='black',activebackground='red', fg=f_g,bg=b_g,variable=finder).pack(padx=1,pady=1)
grat = StringVar()
grat.set("0")
tk.Checkbutton(options_frame,text='graticule',width=13,anchor="w",highlightbackground='black',activebackground='red',bg=b_g,fg=f_g, variable=grat).pack(padx=1,pady=1)
polaris = StringVar()
polaris.set("0")
tk.Checkbutton(options_frame,text='Polaris image',width=13,anchor="w",highlightbackground='black',activebackground='red',bg=b_g,fg=f_g, variable=polaris).pack(padx=1,pady=1)
test = StringVar()
test.set(param['Test mode'])
tk.Checkbutton(options_frame,text='M13 image',width=13,anchor="w",highlightbackground='black',activebackground='red',bg=b_g,fg=f_g, variable=test).pack(padx=1,pady=1)


#tk.Label(window,text='ccd is '+camType,bg=b_g,fg=f_g).place(x=20,y=444)
#tk.Label(window,text ='Nexus '+NexStr,bg=b_g,fg=f_g).place(x=20,y=466)

box_write('ccd is '+camType)
box_write('Nexus '+NexStr)

but_frame = Frame(window,bg='black')
but_frame.place(x=25,y=650)
tk.Button(but_frame, text='Align',bg=b_g,fg=f_g,activebackground='red',highlightbackground='red',bd=0,height=2,width=10,command=align).pack(padx=1,pady=40)
tk.Button(but_frame, text='Capture',activebackground='red',highlightbackground='red',bd=0,bg=b_g,fg=f_g,height=2,width=10,command=image).pack(padx=1,pady=10)
tk.Button(but_frame, text='Solve',activebackground='red',highlightbackground='red',bd=0,height=2,width=10,bg=b_g,fg=f_g,command=solve).pack(padx=1,pady=10)
tk.Button(but_frame, text='Finish GoTo',activebackground='red',highlightbackground='red',bd=0,height=2,width=10,bg=b_g,fg=f_g,command=goto).pack(padx=1,pady=10)
tk.Button(but_frame, text='Move to Finish',activebackground='red',highlightbackground='red',bd=0,height=2,width=10,bg=b_g,fg=f_g,command=move).pack(padx=1,pady=10)

off_frame = Frame(window,bg='black')
off_frame.place(x=10,y=420)
tk.Button(off_frame, text='Measure',activebackground='red',highlightbackground='red',bd=0,height=1,width=8,bg=b_g,fg=f_g,command=measure_offset).pack(padx=1,pady=1)
tk.Button(off_frame, text='Use New',bg=b_g,fg=f_g,activebackground='red',highlightbackground='red',bd=0,height=1,width=8,command=use_new).pack(padx=1,pady=1)
tk.Button(off_frame, text='Save Offset',activebackground='red',highlightbackground='red',bd=0,bg=b_g,fg=f_g,height=1,width=8,command=save_offset).pack(padx=1,pady=1)
tk.Button(off_frame, text='Use Saved',activebackground='red',highlightbackground='red',bd=0,bg=b_g,fg=f_g,height=1,width=8,command=use_loaded_offset).pack(padx=1,pady=1)
tk.Button(off_frame, text='Reset Offset',activebackground='red',highlightbackground='red',bd=0,bg=b_g,fg=f_g,height=1,width=8,command=reset_offset).pack(padx=1,pady=1)
d_x,d_y,dxstr,dystr = pixel2dxdy(offset[0],offset[1])


#tk.Label(window,text='not measured',bg=b_g,fg=f_g).place(x=110,y=400)
tk.Label(window,text='Offset:',bg=b_g,fg=f_g).place(x=10,y=400)
tk.Label(window,text='0,0',bg=b_g,fg=f_g,width=6).place(x=60,y=400)
#tk.Label(window,text='dx,dy arc min',bg=b_g,fg=f_g).place(x=80,y=400)
nex_frame = Frame(window,bg='black')
nex_frame.place(x=250,y=766)
tk.Button(nex_frame, text='Nexus',bg=b_g,fg=f_g,activebackground='red',highlightbackground='red',bd=0,command=readNexus).pack(padx=1,pady=1)

tk.Label(window,text='Solution',bg=b_g,fg=f_g).place(x=345,y=770)
tk.Label(window,text='delta (dx,dy)',bg=b_g,fg=f_g).place(x=425,y=770)

dis_frame = Frame(window,bg='black')
dis_frame.place(x=550,y=765)
tk.Button(dis_frame,text='Display',bg=b_g,fg=f_g,activebackground='red',anchor='w',highlightbackground='red',bd=0,width = 8,command=image_show).pack(padx=1,pady=1)
lock = StringVar()
lock.set("0")
tk.Checkbutton(dis_frame,text='Scope centre',bg=b_g, fg=f_g,activebackground='red',anchor='w',highlightbackground='black',bd=0,width=10, variable=lock).pack(padx=1,pady=1)
zoom = StringVar()
zoom.set("0")
tk.Checkbutton(dis_frame,text='zoom x2',bg=b_g, fg=f_g,activebackground='red',anchor='w',highlightbackground='black',bd=0,width=10, variable=zoom).pack(padx=1,pady=1)
flip = StringVar()
flip.set("0")
tk.Checkbutton(dis_frame,text='flip',bg=b_g, fg=f_g,activebackground='red',anchor='w',highlightbackground='black',bd=0,width=10, variable=flip).pack(padx=1,pady=1)
mirror = StringVar()
mirror.set("0")
tk.Checkbutton(dis_frame,text='mirror',bg=b_g, fg=f_g,activebackground='red',anchor='w',highlightbackground='black',bd=0,width=10, variable=mirror).pack(padx=1,pady=1)
auto_rotate = StringVar()
auto_rotate.set("0")
tk.Checkbutton(dis_frame,text='auto-rotate',bg=b_g, fg=f_g,activebackground='red',anchor='w',highlightbackground='black',bd=0,width=10, variable=auto_rotate).pack(padx=1,pady=1)
manual_rotate = StringVar()
manual_rotate.set("1")
tk.Checkbutton(dis_frame,text='rotate angle',bg=b_g, fg=f_g,activebackground='red',anchor='w',highlightbackground='black',bd=0,width=10, variable=manual_rotate).pack(padx=1,pady=1)
angle = StringVar()
angle.set("0")
tk.Entry(dis_frame,textvariable=angle,bg='red',fg=b_g,highlightbackground='red',bd=0,width = 5).pack(padx=10,pady=1)


ann_frame = Frame(window,bg='black')
ann_frame.place(x=700,y=765)
tk.Button(ann_frame,text='Annotate',bg=b_g, fg=f_g,activebackground='red',anchor='w',highlightbackground='red',bd=0,width=6, command=annotate_image).pack(padx=1,pady=1)
bright = StringVar()
bright.set("0")
tk.Checkbutton(ann_frame,text='Bright',bg=b_g,fg=f_g,activebackground='red',anchor='w',highlightbackground='black',bd=0,width = 8,variable=bright).pack(padx=1,pady=1)
hip = StringVar()
hip.set("0")
tk.Checkbutton(ann_frame,text='Hip',bg=b_g,fg=f_g,activebackground='red',anchor='w',highlightbackground='black',bd=0,width = 8,variable=hip).pack(padx=1,pady=1)
hd = StringVar()
hd.set("0")
tk.Checkbutton(ann_frame,text='H-D',bg=b_g,fg=f_g,activebackground='red',anchor='w',highlightbackground='black',bd=0,width = 8,variable=hd).pack(padx=1,pady=1)
ngc= StringVar()
ngc.set("0")
tk.Checkbutton(ann_frame,text='ngc/ic',bg=b_g,fg=f_g,activebackground='red',anchor='w',highlightbackground='black',bd=0,width = 8,variable=ngc).pack(padx=1,pady=1)
abell = StringVar()
abell.set("0")
tk.Checkbutton(ann_frame,text='Abell',bg=b_g,fg=f_g,activebackground='red',anchor='w',highlightbackground='black',bd=0,width = 8,variable=abell).pack(padx=1,pady=1)
tycho2 = StringVar()
tycho2.set("0")
tk.Checkbutton(ann_frame,text='Tycho2',bg=b_g,fg=f_g,activebackground='red',anchor='w',highlightbackground='black',bd=0,width = 8,variable=tycho2).pack(padx=1,pady=1)

tk.Label(window,text='RA',bg=b_g,fg=f_g).place(x=200,y=804)
tk.Label(window,text='Dec',bg=b_g,fg=f_g).place(x=200,y=826)
tk.Label(window,text='Az',bg=b_g,fg=f_g).place(x=200,y=870)
tk.Label(window,text='Alt',bg=b_g,fg=f_g).place(x=200,y=892)

EP = StringVar()
EP.set("0")
EP_frame = Frame(window,bg='black')
EP_frame.place(x=1060,y=770)
rad13 = Checkbutton(EP_frame,text='FOV indicator',bg=b_g,fg=f_g,activebackground='red',anchor='w', \
                    highlightbackground='black',bd=0,width=12, variable=EP).pack(padx=1,pady=2)
EPlength = StringVar()
EPlength.set(float(param['default_eyepiece']))
for i in range(len(eye_piece)):
    tk.Radiobutton(EP_frame,text=eye_piece[i][0],bg=b_g,fg=f_g,activebackground='red',anchor='w', \
                   highlightbackground='black',bd=0, width = 20,value=eye_piece[i][1]*eye_piece[i][2], variable=EPlength).pack(padx=1,pady=0)
get_offset()
window.protocol('WM_DELETE_WINDOW', on_closing)
window.mainloop()

