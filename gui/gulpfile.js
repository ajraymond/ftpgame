var gulp = require('gulp');
var jshint= require('gulp-jshint');
var csslint = require('gulp-csslint');

gulp.task('default', ['jshint', 'csslint']);

gulp.task('csslint', function() {
    gulp.src('css/*.css')
      .pipe(csslint())
      .pipe(csslint.reporter());
});

gulp.task('jshint', function() {
  return gulp.src('js/**/*.js')
    .pipe(jshint())
    .pipe(jshint.reporter('jshint-stylish'));
});
