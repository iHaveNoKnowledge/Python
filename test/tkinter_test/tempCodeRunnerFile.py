self.pass_input = Entry(
            self.subwin_frame, textvariable=self.app.user_pw, show="*", validate="key", validatecommand=(self.app.validate_input, "%P"))