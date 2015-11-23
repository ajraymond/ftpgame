var gulp = require('gulp');
var jshint= require('gulp-jshint');

gulp.task('default', ['jshint']);

gulp.task('jshint', function() {
  return gulp.src('js/**/*.js')
    .pipe(jshint())
    .pipe(jshint.reporter('jshint-stylish'));
});
