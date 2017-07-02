var path = require('path');
var fs = require('fs');
var webpack = require('webpack');


module.exports = [
    {
        entry: {
            main: '.' + path.sep + path.join('src_js', 'hatter', 'main')
        },
        output: {
            filename: '[name].js',
            path: path.join(__dirname, 'build', 'jshatter')
        },
        module: {
            rules: [
                {
                    test: /\.js$/,
                    exclude: /node_modules/,
                    use: {
                        loader: 'babel-loader'
                    }
                },
                {
                    test: /\.scss$/,
                    use: ["style-loader", "css-loader", "resolve-url-loader", "sass-loader?sourceMap"]
                },

                // TODO isolate fonts only
                { test: /\.woff(\?v=\d+\.\d+\.\d+)?$/, use: "url-loader?name=fonts/[hash].[ext]&limit=10000&mimetype=application/font-woff" },
                { test: /\.woff2(\?v=\d+\.\d+\.\d+)?$/, use: "url-loader?name=fonts/[hash].[ext]&limit=10000&mimetype=application/font-woff" },
                { test: /\.ttf(\?v=\d+\.\d+\.\d+)?$/, use: "url-loader?name=fonts/[hash].[ext]&limit=10000&mimetype=application/octet-stream" },
                { test: /\.eot(\?v=\d+\.\d+\.\d+)?$/, use: "file-loader?name=fonts/[hash].[ext]" },
                { test: /\.svg(\?v=\d+\.\d+\.\d+)?$/, use: "url-loader?name=fonts/[hash].[ext]&limit=10000&mimetype=image/svg+xml" }
            ]
        },
        resolve: {
            modules: [
                path.join(__dirname, 'src_js'),
                path.join(__dirname, 'src_web'),
                path.join(__dirname, 'node_modules')
            ]
        },
        resolveLoader: {
            alias: {
                static: 'file-loader?context=src_web/static&name=[path][name].[ext]'
            }
        },
        devtool: 'source-map'
    }
];
