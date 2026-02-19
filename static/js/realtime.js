// realtime.js
// Connects to /ws/users and listens for broadcasts from the server.
(function(){
    const url = (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws/users';
    let ws;

    function connect(){
        ws = new WebSocket(url);
        ws.onopen = function(){
            console.debug('Realtime socket connected');
            // send a small hello so server can ack
            ws.send('hello');
        };
        ws.onmessage = function(evt){
            try{
                const text = evt.data;
                // Expect simple text messages like 'user:update:{json}' or plain JSON
                console.debug('Realtime message:', text);
                // Allow pages to subscribe by implementing window.onRealtimeMessage
                if(window.onRealtimeMessage){
                    window.onRealtimeMessage(text);
                }
            }catch(e){
                console.error('Error handling realtime message', e);
            }
        };
        ws.onclose = function(){
            console.debug('Realtime socket closed, reconnecting in 2s');
            setTimeout(connect, 2000);
        };
        ws.onerror = function(err){
            console.error('Realtime socket error', err);
            ws.close();
        };
    }

    // Expose a simple send function
    window.sendRealtime = function(msg){
        if(ws && ws.readyState === WebSocket.OPEN) ws.send(msg);
    }

    connect();
})();
