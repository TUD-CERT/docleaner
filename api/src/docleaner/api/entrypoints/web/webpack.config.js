const miniCssExtractPlugin = require("/srv/node_modules/mini-css-extract-plugin")
const path = require("path")

module.exports = {
    entry: "./static/js/main.js",
    output: {
        filename: "bundle.js",
        path: path.resolve(__dirname, "static/dist")
    },
    plugins: [new miniCssExtractPlugin({filename: "bundle.css"})],
    resolve: {
        modules: ["/srv/node_modules"]
    },
    module: {
        rules: [{
            test: /\.(scss)$/,
            use: [
                {
                    // Extracts CSS for each JS file that includes CSS
                    loader: miniCssExtractPlugin.loader
                },
                {
                    loader: "css-loader"
                },
                {
                    loader: "postcss-loader",
                    options: {
                        postcssOptions: {
                            plugins: () => [
                                require("autoprefixer")
                            ]
                        }
                    }
                },
                {
                    loader: "sass-loader"
                }
            ]
        }]
    }
}