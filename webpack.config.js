var path = require('path');


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
                    test: /\.scss$/,
                    use: ["style-loader", "css-loader", "resolve-url-loader", "sass-loader?sourceMap"]
                },
                {
                    test: /node_modules.*\.(woff|woff2|ttf|eot|svg)$/,
                    use: "file-loader?name=fonts/[hash].[ext]"
                }
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
