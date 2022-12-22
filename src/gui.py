from skyfield.api import load, Star, wgs84
import tkinter as tk
from tkinter import Label, Radiobutton, StringVar, Checkbutton, Button, Frame
from PIL import Image, ImageTk, ImageDraw, ImageOps
from pathlib import Path
from common import AstroData, CameraData, CLIData, Common, OffsetData
import logging
from Coordinates import Coordinates
import threading
import sys


class EFinderGUI():
    f_g = "red"
    b_g = "black"
    LST, lbl_LST, lbl_UTC, lbl_date, nexus, sidereal = None, None, None, None, None, None
    exposure = 1.0
    # planets and earth not used
    planets = load("de421.bsp")
    earth = planets["earth"]
    ts = load.timescale()
    window = tk.Tk()
    box_list = ["", "", "", "", "", ""]
    eye_piece = []

    def __init__(self, nexus, param, camera_data: CameraData,
                 cli_data: CLIData, astro_data: AstroData,
                 offset_data: OffsetData, common: Common,
                 coordinates: Coordinates):
        self.nexus = nexus
        self.param = param
        self.camera_data = camera_data
        self.common = common
        self.coordinates = coordinates
        self.cli_data = cli_data
        self.astro_data: AstroData = astro_data
        self.offset_data: OffsetData = offset_data
        self.cwd_path: Path = Path.cwd()

    def start_loop(self):
        # main program loop, using tkinter GUI
        self.window.title("ScopeDog eFinder v" + self.common.get_version())
        self.window.geometry("1300x1000+100+10")
        self.window.configure(bg="black")
        self.window.bind("<<OLED_Button>>", self.do_button)
        self.setup_sidereal()
        # self.sidereal()
        # self.update_nexus_GUI()
        NexStr = self.astro_data.nexus.get_nex_str()
        self.draw_screen(NexStr)

        # sid = threading.Thread(target=self.sidereal)
        # sid.daemon = True
        # sid.start()

    def update_nexus_GUI(self):
        """Put the correct nexus numbers on the GUI."""
        logging.debug("update_nexus_GUI")
        self.astro_data.nexus.read_altAz()
        nexus_radec = self.astro_data.nexus.get_radec()
        nexus_altaz = self.astro_data.nexus.get_altAz()
        tk.Label(
            self.window,
            width=10,
            text=self.coordinates.hh2dms(nexus_radec[0]),
            anchor="e",
            bg=self.b_g,
            fg=self.f_g,
        ).place(x=225, y=804)
        tk.Label(
            self.window,
            width=10,
            anchor="e",
            text=self.coordinates.dd2dms(nexus_radec[1]),
            bg=self.b_g,
            fg=self.f_g,
        ).place(x=225, y=826)
        tk.Label(
            self.window,
            width=10,
            anchor="e",
            text=self.coordinates.ddd2dms(nexus_altaz[1]),
            bg=self.b_g,
            fg=self.f_g,
        ).place(x=225, y=870)
        tk.Label(
            self.window,
            width=10,
            anchor="e",
            text=self.coordinates.dd2dms(nexus_altaz[0]),
            bg=self.b_g,
            fg=self.f_g,
        ).place(x=225, y=892)

    def do_button(self, event):
        logging.info(f"do_button with {event=}")
    #     global handpad, coordinates, solved_radec
    #     logging.debug(f"button event: {button}")
    #     if button == "21":
    #         handpad.display("Capturing image", "", "")
    #         read_nexus_and_capture()
    #         handpad.display("Solving image", "", "")
    #         solve()
    #         handpad.display(
    #             "RA:  " + coordinates.hh2dms(solved_radec[0]),
    #             "Dec:" + coordinates.dd2dms(solved_radec[1]),
    #             "d:" + str(deltaAz)[:6] + "," + str(deltaAlt)[:6],
    #         )
    #     elif button == "17":  # up button
    #         handpad.display("Performing", "  align", "")
    #         align()
    #         handpad.display(
    #             "RA:  " + coordinates.hh2dms(solved_radec[0]),
    #             "Dec:" + coordinates.dd2dms(solved_radec[1]),
    #             "Report:" + p,
    #         )
    #     elif button == "19":  # down button
    #         handpad.display("Performing", "   GoTo++", "")
    #         goto()
    #         handpad.display(
    #             "RA:  " + coordinates.hh2dms(solved_radec[0]),
    #             "Dec:" + coordinates.dd2dms(solved_radec[1]),
    #             "d:" + str(deltaAz)[:6] + "," + str(deltaAlt)[:6],
    #         )

    def solve_image_failed(self, elapsed_time, b_g=None, f_g=None):
        self.box_write("Solve Failed", True)
        if b_g is None or f_g is None:
            b_g = self.b_g
            f_g = self.f_g
        tk.Label(
            self.window, width=10, anchor="e", text="no solution", bg=b_g, fg=f_g
        ).place(x=410, y=804)
        tk.Label(
            self.window, width=10, anchor="e", text="no solution", bg=b_g, fg=f_g
        ).place(x=410, y=826)
        tk.Label(
            self.window, width=10, anchor="e", text="no solution", bg=b_g, fg=f_g
        ).place(x=410, y=870)
        tk.Label(
            self.window, width=10, anchor="e", text="no solution", bg=b_g, fg=f_g
        ).place(x=410, y=892)
        tk.Label(self.window, text=elapsed_time,
                 bg=b_g, fg=f_g).place(x=315, y=936)

    def solve_image_success(self, solved_radec, solved_altaz):
        tk.Label(
            self.window,
            width=10,
            text=coordinates.hh2dms(solved_radec[0]),
            anchor="e",
            bg=self.b_g,
            fg=self.f_g,
        ).place(x=410, y=804)
        tk.Label(
            self.window,
            width=10,
            anchor="e",
            text=coordinates.dd2dms(solved_radec[1]),
            bg=self.b_g,
            fg=self.f_g,
        ).place(x=410, y=826)
        tk.Label(
            self.window,
            width=10,
            anchor="e",
            text=coordinates.ddd2dms(solved_altaz[1]),
            bg=self.b_g,
            fg=self.f_g,
        ).place(x=410, y=870)
        tk.Label(
            self.window,
            width=10,
            anchor="e",
            text=coordinates.dd2dms(solved_altaz[0]),
            bg=self.b_g,
            fg=self.f_g,
        ).place(x=410, y=892)

    def solve_elapsed_time(self, elapsed_time_str):
        tk.Label(self.window, text=elapsed_time_str, width=20, anchor="e", bg=self.b_g, fg=self.f_g).place(
            x=315, y=936)

    def image_show(self):
        # global manual_angle, img3, EPlength, scopeAlt
        img2 = Image.open(self.cli_data.images_path / "capture.jpg")
        width, height = img2.size
        # original is 1280 x 960
        img2 = img2.resize((1014, 760), Image.LANCZOS)
        width, height = img2.size
        # vertical finder field of view in arc min
        h = self.camera_data.pix_scale * 960 / 60
        w = self.camera_data.pix_scale * 1280 / 60
        w_offset = width * offset[0] * 60 / w
        h_offset = height * offset[1] * 60 / h
        img2 = img2.convert("RGB")
        if self.grat.get() == "1":
            draw = ImageDraw.Draw(img2)
            draw.line([(width / 2, 0), (width / 2, height)], fill=75, width=2)
            draw.line([(0, height / 2), (width, height / 2)], fill=75, width=2)
            draw.line(
                [(width / 2 + w_offset, 0), (width / 2 + w_offset, height)],
                fill=255,
                width=1,
            )
            draw.line(
                [(0, height / 2 - h_offset), (width, height / 2 - h_offset)],
                fill=255,
                width=1,
            )
        if EP.get() == "1":
            draw = ImageDraw.Draw(img2)
            tfov = (
                (float(EPlength.get()) * height /
                 float(self.param["scope_focal_length"]))
                * 60
                / h
            ) / 2  # half tfov in pixels
            draw.ellipse(
                [
                    width / 2 + w_offset - tfov,
                    height / 2 - h_offset - tfov,
                    width / 2 + w_offset + tfov,
                    height / 2 - h_offset + tfov,
                ],
                fill=None,
                outline=255,
                width=1,
            )
        if lock.get() == "1":
            img2 = zoom_at(img2, w_offset, h_offset, 1)
        if zoom.get() == "1":
            img2 = zoom_at(img2, 0, 0, 2)
        if flip.get() == "1":
            img2 = ImageOps.flip(img2)
        if mirror.get() == "1":
            img2 = ImageOps.mirror(img2)
        if auto_rotate.get() == "1":
            img2 = img2.rotate(scopeAlt)
        elif manual_rotate.get() == "1":
            angle_deg = angle.get()
            img2 = img2.rotate(float(angle_deg))
        img3 = img2
        img2 = ImageTk.PhotoImage(img2)
        panel.configure(image=img2)
        panel.image = img2
        panel.place(x=200, y=5, width=1014, height=760)

    # GUI specific

    def setup_sidereal(self):
        # global LST, lbl_LST, lbl_UTC, lbl_date, ts, nexus, window
        logging.info("setup_sidereal")
        b_g = self.b_g
        f_g = self.f_g
        t = self.ts.now()
        self.LST = t.gmst + self.astro_data.nexus.get_long() / 15  # as decimal hours
        LSTstr = (
            str(int(self.LST))
            + "h "
            + str(int((self.LST * 60) % 60))
            + "m "
            + str(int((self.LST * 3600) % 60))
            + "s"
        )
        self.lbl_LST = Label(self.window, bg=b_g, fg=f_g, text=LSTstr)
        self.lbl_LST.place(x=55, y=44)
        self.lbl_UTC = Label(self.window, bg=b_g, fg=f_g,
                             text=t.utc_strftime("%H:%M:%S"))
        self.lbl_UTC.place(x=55, y=22)
        self.lbl_date = Label(self.window, bg=b_g, fg=f_g,
                              text=t.utc_strftime("%d %b %Y"))
        self.lbl_date.place(x=55, y=0)

    # GUI specific

    def sidereal(self):
        logging.debug("sidereal")
        t = self.ts.now()
        self.LST = t.gmst + self.nexus.get_long() / 15  # as decimal hours
        LSTstr = (
            str(int(self.LST))
            + "h "
            + str(int((self.LST * 60) % 60))
            + "m "
            + str(int((self.LST * 3600) % 60))
            + "s"
        )
        self.lbl_LST.config(text=LSTstr)
        self.lbl_UTC.config(text=t.utc_strftime("%H:%M:%S"))
        self.lbl_date.config(text=t.utc_strftime("%d %b %Y"))
        self.lbl_LST.after(1000, self.sidereal)

# the offset methods:

    def save_offset(self):
        self.param["d_x"], self.param["d_y"] = offset
        self.save_param()
        self.get_offset()
        self.box_write("offset saved", True)

    def get_offset(self):
        x_offset_saved, y_offset_saved, dxstr_saved, dystr_saved = self.common.dxdy2pixel(
            float(self.param["d_x"]), float(self.param["d_y"])
        )
        tk.Label(
            self.window,
            text=dxstr_saved + "," + dystr_saved + "          ",
            width=9,
            anchor="w",
            bg=self.b_g,
            fg=self.f_g,
        ).place(x=110, y=520)

    def use_saved_offset(self):
        global offset
        x_offset_saved, y_offset_saved, dxstr, dystr = self.common.dxdy2pixel(
            float(self.param["d_x"]), float(self.param["d_y"])
        )
        offset = float(self.param["d_x"]), float(self.param["d_y"])
        tk.Label(self.window, text=dxstr + "," + dystr, bg=self.b_g, fg=self.f_g, width=8).place(
            x=60, y=400
        )

    def use_new_offset(self):
        global offset, offset_new
        offset = offset_new
        x_offset_new, y_offset_new, dxstr, dystr = self.common.dxdy2pixel(
            offset[0], offset[1])
        tk.Label(window, text=dxstr + "," + dystr, bg=b_g, fg=f_g, width=8).place(
            x=60, y=400
        )

    def reset_offset(self):
        global offset
        offset = offset_reset
        eFinderGUI.box_write("offset reset", True)
        tk.Label(window, text="0,0", bg=b_g,
                 fg="red", width=8).place(x=60, y=400)
###########################################

    def draw_screen(self, NexStr):
        b_g = self.b_g
        f_g = self.f_g
        tk.Label(self.window, text="Date", fg=f_g, bg=b_g).place(x=15, y=0)
        tk.Label(self.window, text="UTC", bg=b_g, fg=f_g).place(x=15, y=22)
        tk.Label(self.window, text="LST", bg=b_g, fg=f_g).place(x=15, y=44)
        tk.Label(self.window, text="Loc:", bg=b_g, fg=f_g).place(x=15, y=66)
        tk.Label(
            self.window,
            width=18,
            anchor="w",
            text=str(self.astro_data.nexus.get_long()) + "\u00b0  " +
            str(self.astro_data.nexus.get_lat()) + "\u00b0",
            bg=b_g,
            fg=f_g,
        ).place(x=55, y=66)
        img = Image.open(self.cwd_path / "splashscreen.jpeg")
        img = img.resize((1014, 760))
        img = ImageTk.PhotoImage(img)
        panel = tk.Label(self.window, highlightbackground="red",
                         highlightthickness=2, image=img)
        panel.place(x=200, y=5, width=1014, height=760)

        self.exposure_str: StringVar = StringVar()
        self.exposure_str.set(str(self.camera_data.exposure))
        exp_frame = Frame(self.window, bg="black")
        exp_frame.place(x=0, y=100)
        tk.Label(exp_frame, text="Exposure", bg=b_g,
                 fg=f_g).pack(padx=1, pady=1)
        expRange = self.cli_data.exp_range
        for i in range(len(expRange)):
            tk.Radiobutton(
                exp_frame,
                text=str(expRange[i]),
                bg=b_g,
                fg=f_g,
                width=7,
                activebackground="red",
                anchor="w",
                highlightbackground="black",
                value=float(expRange[i]),
                variable=self.exposure_str
            ).pack(padx=1, pady=1)

        gain = StringVar()
        gain.set(str(self.camera_data.gain))
        gain_frame = Frame(self.window, bg="black")
        gain_frame.place(x=80, y=100)
        tk.Label(gain_frame, text="Gain", bg=b_g, fg=f_g).pack(padx=1, pady=1)
        gainRange = self.cli_data.gain_range
        for i in range(len(gainRange)):
            tk.Radiobutton(
                gain_frame,
                text=str(gainRange[i]),
                bg=b_g,
                fg=f_g,
                width=7,
                activebackground="red",
                anchor="w",
                highlightbackground="black",
                value=float(gainRange[i]),
                variable=self.camera_data.gain,
            ).pack(padx=1, pady=1)

        options_frame = Frame(self.window, bg="black")
        options_frame.place(x=20, y=270)
        polaris = StringVar()
        polaris.set("0")
        tk.Checkbutton(
            options_frame,
            text="Polaris image",
            width=13,
            anchor="w",
            highlightbackground="black",
            activebackground="red",
            bg=b_g,
            fg=f_g,
            variable=polaris,
        ).pack(padx=1, pady=1)
        m31 = StringVar()
        m31.set("0")
        tk.Checkbutton(
            options_frame,
            text="M31 image",
            width=13,
            anchor="w",
            highlightbackground="black",
            activebackground="red",
            bg=b_g,
            fg=f_g,
            variable=m31,
        ).pack(padx=1, pady=1)

        self.box_write(
            "ccd is " + self.camera_data.camera.get_cam_type(), False)
        self.box_write("Nexus " + NexStr, True)

        but_frame = Frame(self.window, bg="black")
        but_frame.place(x=25, y=650)
        tk.Button(
            but_frame,
            text="Align",
            bg=b_g,
            fg=f_g,
            activebackground="red",
            highlightbackground="red",
            bd=0,
            height=2,
            width=10,
            command=self.align,
        ).pack(padx=1, pady=40)
        tk.Button(
            but_frame,
            text="Capture",
            activebackground="red",
            highlightbackground="red",
            bd=0,
            bg=b_g,
            fg=f_g,
            height=2,
            width=10,
            command=self.read_nexus_and_capture,
        ).pack(padx=1, pady=5)
        tk.Button(
            but_frame,
            text="Solve",
            activebackground="red",
            highlightbackground="red",
            bd=0,
            height=2,
            width=10,
            bg=b_g,
            fg=f_g,
            command=self.solve,
        ).pack(padx=1, pady=5)
        tk.Button(
            but_frame,
            text="GoTo: via Align",
            activebackground="red",
            highlightbackground="red",
            bd=0,
            height=2,
            width=10,
            bg=b_g,
            fg=f_g,
            command=self.goto,
        ).pack(padx=1, pady=5)
        tk.Button(
            but_frame,
            text="GoTo: via Move",
            activebackground="red",
            highlightbackground="red",
            bd=0,
            height=2,
            width=10,
            bg=b_g,
            fg=f_g,
            command=self.move,
        ).pack(padx=1, pady=5)

        off_frame = Frame(self.window, bg="black")
        off_frame.place(x=10, y=420)
        tk.Button(
            off_frame,
            text="Measure",
            activebackground="red",
            highlightbackground="red",
            bd=0,
            height=1,
            width=8,
            bg=b_g,
            fg=f_g,
            command=self.measure_offset,
        ).pack(padx=1, pady=1)
        tk.Button(
            off_frame,
            text="Use New",
            bg=b_g,
            fg=f_g,
            activebackground="red",
            highlightbackground="red",
            bd=0,
            height=1,
            width=8,
            command=self.use_new_offset,
        ).pack(padx=1, pady=1)
        tk.Button(
            off_frame,
            text="Save Offset",
            activebackground="red",
            highlightbackground="red",
            bd=0,
            bg=b_g,
            fg=f_g,
            height=1,
            width=8,
            command=self.save_offset,
        ).pack(padx=1, pady=1)
        tk.Button(
            off_frame,
            text="Use Saved",
            activebackground="red",
            highlightbackground="red",
            bd=0,
            bg=b_g,
            fg=f_g,
            height=1,
            width=8,
            command=self.use_saved_offset,
        ).pack(padx=1, pady=1)
        tk.Button(
            off_frame,
            text="Reset Offset",
            activebackground="red",
            highlightbackground="red",
            bd=0,
            bg=b_g,
            fg=f_g,
            height=1,
            width=8,
            command=self.reset_offset,
        ).pack(padx=1, pady=1)
        d_x, d_y, dxstr, dystr = self.common.pixel2dxdy(self.offset_data.offset[0],
                                                        self.offset_data.offset[1])

        tk.Label(self.window, text="Offset:",
                 bg=b_g, fg=f_g).place(x=10, y=400)
        tk.Label(self.window, text="0,0", bg=b_g,
                 fg=f_g, width=6).place(x=60, y=400)

        nex_frame = Frame(self.window, bg="black")
        nex_frame.place(x=250, y=766)
        tk.Button(
            nex_frame,
            text="Nexus",
            bg=b_g,
            fg=f_g,
            activebackground="red",
            highlightbackground="red",
            bd=0,
            command=self.update_nexus_GUI,
        ).pack(padx=1, pady=1)

        tk.Label(self.window, text="delta x,y",
                 bg=b_g, fg=f_g).place(x=345, y=770)
        tk.Label(self.window, text="Solution",
                 bg=b_g, fg=f_g).place(x=435, y=770)
        tk.Label(self.window, text="delta x,y",
                 bg=b_g, fg=f_g).place(x=535, y=770)
        target_frame = Frame(self.window, bg="black")
        target_frame.place(x=620, y=766)
        tk.Button(
            target_frame,
            text="Target",
            bg=b_g,
            fg=f_g,
            activebackground="red",
            highlightbackground="red",
            bd=0,
            command=self.readTarget,
        ).pack(padx=1, pady=1)

        dis_frame = Frame(self.window, bg="black")
        dis_frame.place(x=800, y=765)
        tk.Button(
            dis_frame,
            text="Display",
            bg=b_g,
            fg=f_g,
            activebackground="red",
            anchor="w",
            highlightbackground="red",
            bd=0,
            width=8,
            command=self.image_show,
        ).pack(padx=1, pady=1)
        grat = StringVar()
        grat.set("0")
        tk.Checkbutton(
            dis_frame,
            text="graticule",
            width=10,
            anchor="w",
            highlightbackground="black",
            activebackground="red",
            bg=b_g,
            fg=f_g,
            variable=grat,
        ).pack(padx=1, pady=1)
        lock = StringVar()
        lock.set("0")
        tk.Checkbutton(
            dis_frame,
            text="Scope centre",
            bg=b_g,
            fg=f_g,
            activebackground="red",
            anchor="w",
            highlightbackground="black",
            bd=0,
            width=10,
            variable=lock,
        ).pack(padx=1, pady=1)
        zoom = StringVar()
        zoom.set("0")
        tk.Checkbutton(
            dis_frame,
            text="zoom x2",
            bg=b_g,
            fg=f_g,
            activebackground="red",
            anchor="w",
            highlightbackground="black",
            bd=0,
            width=10,
            variable=zoom,
        ).pack(padx=1, pady=1)
        flip = StringVar()
        flip.set("0")
        tk.Checkbutton(
            dis_frame,
            text="flip",
            bg=b_g,
            fg=f_g,
            activebackground="red",
            anchor="w",
            highlightbackground="black",
            bd=0,
            width=10,
            variable=flip,
        ).pack(padx=1, pady=1)
        mirror = StringVar()
        mirror.set("0")
        tk.Checkbutton(
            dis_frame,
            text="mirror",
            bg=b_g,
            fg=f_g,
            activebackground="red",
            anchor="w",
            highlightbackground="black",
            bd=0,
            width=10,
            variable=mirror,
        ).pack(padx=1, pady=1)
        auto_rotate = StringVar()
        auto_rotate.set("0")
        tk.Checkbutton(
            dis_frame,
            text="auto-rotate",
            bg=b_g,
            fg=f_g,
            activebackground="red",
            anchor="w",
            highlightbackground="black",
            bd=0,
            width=10,
            variable=auto_rotate,
        ).pack(padx=1, pady=1)
        manual_rotate = StringVar()
        manual_rotate.set("1")
        tk.Checkbutton(
            dis_frame,
            text="rotate angle",
            bg=b_g,
            fg=f_g,
            activebackground="red",
            anchor="w",
            highlightbackground="black",
            bd=0,
            width=10,
            variable=manual_rotate,
        ).pack(padx=1, pady=1)
        angle = StringVar()
        angle.set("0")
        tk.Entry(
            dis_frame,
            textvariable=angle,
            bg="red",
            fg=b_g,
            highlightbackground="red",
            bd=0,
            width=5,
        ).pack(padx=10, pady=1)

        ann_frame = Frame(self.window, bg="black")
        ann_frame.place(x=950, y=765)
        tk.Button(
            ann_frame,
            text="Annotate",
            bg=b_g,
            fg=f_g,
            activebackground="red",
            anchor="w",
            highlightbackground="red",
            bd=0,
            width=6,
            command=self.annotate_image,
        ).pack(padx=1, pady=1)
        bright = StringVar()
        bright.set("0")
        tk.Checkbutton(
            ann_frame,
            text="Bright",
            bg=b_g,
            fg=f_g,
            activebackground="red",
            anchor="w",
            highlightbackground="black",
            bd=0,
            width=8,
            variable=bright,
        ).pack(padx=1, pady=1)
        hip = StringVar()
        hip.set("0")
        tk.Checkbutton(
            ann_frame,
            text="Hip",
            bg=b_g,
            fg=f_g,
            activebackground="red",
            anchor="w",
            highlightbackground="black",
            bd=0,
            width=8,
            variable=hip,
        ).pack(padx=1, pady=1)
        hd = StringVar()
        hd.set("0")
        tk.Checkbutton(
            ann_frame,
            text="H-D",
            bg=b_g,
            fg=f_g,
            activebackground="red",
            anchor="w",
            highlightbackground="black",
            bd=0,
            width=8,
            variable=hd,
        ).pack(padx=1, pady=1)
        ngc = StringVar()
        ngc.set("0")
        tk.Checkbutton(
            ann_frame,
            text="ngc/ic",
            bg=b_g,
            fg=f_g,
            activebackground="red",
            anchor="w",
            highlightbackground="black",
            bd=0,
            width=8,
            variable=ngc,
        ).pack(padx=1, pady=1)
        abell = StringVar()
        abell.set("0")
        tk.Checkbutton(
            ann_frame,
            text="Abell",
            bg=b_g,
            fg=f_g,
            activebackground="red",
            anchor="w",
            highlightbackground="black",
            bd=0,
            width=8,
            variable=abell,
        ).pack(padx=1, pady=1)
        tycho2 = StringVar()
        tycho2.set("0")
        tk.Checkbutton(
            ann_frame,
            text="Tycho2",
            bg=b_g,
            fg=f_g,
            activebackground="red",
            anchor="w",
            highlightbackground="black",
            bd=0,
            width=8,
            variable=tycho2,
        ).pack(padx=1, pady=1)

        tk.Label(self.window, text="RA", bg=b_g, fg=f_g).place(x=200, y=804)
        tk.Label(self.window, text="Dec", bg=b_g, fg=f_g).place(x=200, y=826)
        tk.Label(self.window, text="Az", bg=b_g, fg=f_g).place(x=200, y=870)
        tk.Label(self.window, text="Alt", bg=b_g, fg=f_g).place(x=200, y=892)

        EP = StringVar()
        EP.set("0")
        EP_frame = Frame(self.window, bg="black")
        EP_frame.place(x=1060, y=770)
        rad13 = Checkbutton(
            EP_frame,
            text="FOV indicator",
            bg=b_g,
            fg=f_g,
            activebackground="red",
            anchor="w",
            highlightbackground="black",
            bd=0,
            width=20,
            variable=EP,
        ).pack(padx=1, pady=2)
        global EPlength
        EPlength = StringVar()
        EPlength.set(float(self.param["default_eyepiece"]))
        for i in range(len(self.eye_piece)):
            tk.Radiobutton(
                EP_frame,
                text=eye_piece[i][0],
                bg=b_g,
                fg=f_g,
                activebackground="red",
                anchor="w",
                highlightbackground="black",
                bd=0,
                width=20,
                value=self.eye_piece[i][1] * self.eye_piece[i][2],
                variable=EPlength,
            ).pack(padx=1, pady=0)
        self.get_offset()
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.window.mainloop()

    def on_closing(self):
        # TODO found out how to save params again
        # self.save_param()
        self.handpad.display("Program closed", "via VNCGUI", "")
        sys.exit()

    def align(self):
        logging.debug("TODO align")

    def read_nexus_and_capture(self):
        logging.debug("TODO read_nexus_and_capture")

    def solve(self):
        logging.debug("TODO solve")

    def goto(self):
        logging.debug("TODO goto")

    def move(self):
        logging.debug("TODO move")

    def measure_offset(self):
        logging.debug("TODO measure_offset")

    def readTarget(self):
        logging.debug("TODO readTarget")

    def annotate_image(self):
        logging.debug("TODO annotate_image")

    def box_write(self, new_line, show_handpad):
        global handpad
        t = self.ts.now()
        for i in range(5, 0, -1):
            self.box_list[i] = self.box_list[i - 1]
        self.box_list[0] = (t.utc_strftime(
            "%H:%M:%S ") + new_line).ljust(36)[:35]
        for i in range(0, 5, 1):
            tk.Label(self.window, text=self.box_list[i], bg=self.b_g, fg=self.f_g).place(
                x=1050, y=980 - i * 16)

    def deltaCalcGUI(self):
        global deltaAz, deltaAlt, solved_altaz
        deltaAz, deltaAlt = self.common.deltaCalc(
            nexus.get_altAz(), solved_altaz, nexus.get_scope_alt(), deltaAz, deltaAlt
        )
        deltaAzstr = "{: .1f}".format(float(deltaAz)).ljust(8)[:8]
        deltaAltstr = "{: .1f}".format(float(deltaAlt)).ljust(8)[:8]
        tk.Label(window, width=10, anchor="e", text=deltaAzstr, bg=b_g, fg=f_g).place(
            x=315, y=870
        )
        tk.Label(window, width=10, anchor="e", text=deltaAltstr, bg=b_g, fg=f_g).place(
            x=315, y=892
        )
