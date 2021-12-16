class SocketWrapper {
    constructor() {
        const current_url = new URL(window.location)
        const socket_url = 'ws://' + current_url.hostname + ':8765/ws'
        this.websocket = new WebSocket(socket_url)
        this.websocket.onmessage = (message) => {
            this._onMessage(message)
        }
        this.waitConnect = new Promise((resolve => this.websocket.onopen = resolve))
        this._listeners = []
        this._once_listeners = []
    }

    _onMessage(message) {
        const {event, data} = JSON.parse(message.data)
        this._listeners.forEach(([e, callback]) => {
            if (event === e) {
                callback(data)
            }
        })
        let indexes = []
        this._once_listeners.forEach(([e, callback], index) => {
            if (event === e) {
                callback(data)
                indexes.push(index)
            }
        })
        for (const index of indexes) {
            this._once_listeners.splice(index, 1)
        }
    }


    on(event, callback) {
        this._listeners.push([event, callback])
    }

    once(event, callback) {
        this._once_listeners.push([event, callback])
    }

    async emit(event, data) {
        await this.waitConnect
        this.websocket.send(JSON.stringify({event, data}))
    }
}


class Server {
    constructor() {
        this.my_id = ""
        this.socket = new SocketWrapper()
        this.chats = []
        this._messages = []
        this.socket.on("disconnected", (data) => {
            let chatIdx = this.chats.findIndex((chat => chat.id === data.id))
            this.chats.splice(chatIdx, 1)
        })
        this.socket.on("message", (data) => {
            this._messages.push(data)
        })
    }

    _listenForJoins() {
        this.socket.on("joined", (data) => {
            this.chats.push(data)
        })
    }

    get_messages(chatId) {
        return this._messages.filter(message => {
            return message.sender_id === chatId || message.sender_id === this.my_id
        })
    }

    async fetchUsers() {
        const response_promise = new Promise((resolve => this.socket.once('fetched_chats', resolve)))
        await this.socket.emit("fetch_chats", {})
        const response = await response_promise
        this.chats = response
        return response
    }

    async join(name) {
        await this.socket.emit("join", {name})
        const response = await new Promise((resolve => this.socket.once('joined', resolve)))
        this._listenForJoins()
        this.my_id = response.id
        return response.id
    }

    async sendToPerson(clientId, message) {
        this._messages.push({message, "sender_id": this.my_id})
        const data = {message, client_id: clientId}
        await this.socket.emit("message", data)
    }

    async sendToGroup(groupId, message) {
        const data = {message: message, group_id: groupId}
        await this.socket.emit("message_to_group", data)
    }

    async createGroup(groupName) {
        const data = {name: groupName}
        await this.socket.emit("create_group", data)
        const response = await new Promise((resolve => this.socket.once('created_group', resolve)))
        this.chats.push(response)
        return response.id
    }

    async addToGroup(groupId, memberId) {
        const data = {event: "add_to_group", data: {group_id: groupId, member_id: memberId}}
        await this.socket.emit(data)
    }

    async removeFromGroup(groupId, memberId) {
        const data = {event: "remove_from_group", data: {group_id: groupId, member_id: memberId}}
        await this.socket.emit(data)
    }
}