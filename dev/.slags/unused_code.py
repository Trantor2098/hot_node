# NOTE UI dyinfo is a legacy solution, not sure if it is still needed.

# dy_info: str|None = None
    # dy_info_icon: str|None = None
    # dy_sub_infos: tuple[str]|None = None
    # dy_info_born_time = 0.0
    # dy_info_duration = 3.0
    
    # @classmethod
    # def set_dynamic_info(cls, info: str, main_icon: str|None = None, sub_infos: tuple[str]|None = None, duration: float = 3.0):
    #     cls.dy_info = info
    #     cls.dy_info_icon = main_icon
    #     cls.dy_sub_infos = sub_infos
    #     cls.dy_info_born_time = time.time()
    #     cls.dy_info_duration = duration
        
    # @classmethod
    # def get_or_expire_dynamic_info(cls):
    #     if cls.dy_info is None:
    #         return None, None, None
    #     if time.time() - cls.dy_info_born_time > cls.dy_info_duration:
    #         cls.dy_info = None
    #         cls.dy_info_icon = None
    #         cls.dy_sub_infos = None
    #         return None, None, None
    #     return cls.dy_info, cls.dy_info_icon, cls.dy_sub_infos

    
    # def draw_dynamic_info(self, layout):
        # Dynamic Info
        # dy_info, dy_info_icon, dy_sub_infos = self.get_or_expire_dynamic_info()
        # if dy_info is not None:
        #     if time.time() - self.dy_info_born_time < self.dy_info_duration:
        #         row = layout.row()
        #         row.label(text=dy_info, icon=dy_info_icon)
        #         if dy_sub_infos is not None:
        #             for info in dy_sub_infos:
        #                 row = layout.row()
        #                 row.label(text=info, icon='BLANK1')