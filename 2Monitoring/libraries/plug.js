var curl = require("curl");
var pwr = [];

module.exports = {
    power_data: async (callback, allIP, interval) => {
        setInterval(() => {
            const getCurl = async (i) => {
                var url = `http://${allIP[i]}/sensor/athom_smart_plug_v2_power`;
                var options = "";

                await curl.get(url, options, async (err, response, body) => {
                    if (err) {
                        // console.log(err);
                        pwr[i + 1] = 0;
                        return;
                    }
                    // console.log(body);
                    // await console.log(JSON.parse(body).value);
                    pwr[i + 1] = await JSON.parse(body).value;
                });
            };

            for (i = 0; i < allIP.length; i++) {
                // console.log(i);
                getCurl(i);
            }
            return callback(pwr);
        }, parseInt(interval));
    },
};
