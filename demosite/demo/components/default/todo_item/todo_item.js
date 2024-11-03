export default {
    lastTitleValue: "",
    inputDeleteDown() {
        this.lastTitleValue = this.title;
    },
    inputDeleteUp() {
        if (this.title === "" && this.lastTitleValue === "") {
            this.delete_item()
        }
    }
}