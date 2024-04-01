def search(self):
        # * ลบ result products list เก่า
        try:
            sku = self.sku.get().strip()
            set = self.set_num.get().strip()

            # * เกี่ยวกับการแสดงผล GUI
            self.clear_log()
            data_dict = self.data_table.get_result(sku, set)
            self.update_log(f"ชื่อชุด: {sku}")
            self.update_log(f"เลขSet: {set}")
            self.sku.set("")
            self.set_num.set("")

            # todo Continue from here// wip you are here
            try:
                self.chromdriver_controller.operation_start(sku, data_dict)
            except ValueError as e:
                error_message = str(e)
                self.update_log(error_message)
        except:
            self.update_log("พัง")
            raise ValueError('search พัง: ', traceback.format_exc())