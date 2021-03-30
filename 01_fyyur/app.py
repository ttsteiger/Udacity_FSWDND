#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
from datetime import datetime
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for, jsonify
from flask_migrate import Migrate
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
from models import *

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format, locale='en')

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')

#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
  # list all venues
  city_state_combinbations = db.session.query(func.count(Venue.id), Venue.city, Venue.state)\
    .group_by(Venue.city, Venue.state).all()

  data = []
  # loop through all available locations and prepare the respective venue data
  for c in city_state_combinbations:
      venues = db.session.query(Venue).filter(Venue.city == c.city, Venue.state == c.state)

      # get info about all venues in a location
      venue_data = []
      for v in venues:
          num_upcoming_shows = len(db.session.query(Show)\
            .filter(Show.venue_id == v.id, Show.start_time > datetime.now()).all())
          venue_data.append({
            'id': v.id,
            'name': v.name,
            'num_upcoming_shows': num_upcoming_shows
          })

      data.append({
        'city': c.city,
        'state': c.state,
        'venues': venue_data
      })

  return render_template('pages/venues.html', areas=data);

@app.route('/venues/search', methods=['POST'])
def search_venues():
  search_term = request.form.get('search_term', '')
  matching_venues = db.session.query(Venue).filter(Venue.name.ilike("%{}%".format(search_term))).all()

  # prepare response data
  data = []
  for v in matching_venues:
      num_upcoming_shows = len(db.session.query(Show)\
        .filter(Show.venue_id == v.id, Show.start_time > datetime.now()).all())
      data.append({
        'id': v.id,
        'name': v.name,
        'num_upcoming_shows': num_upcoming_shows
      })

  response={
    "count": len(data),
    "data": data
  }
  return render_template('pages/search_venues.html', results=response, search_term=search_term)

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  # shows the venue page with the given venue_id
  venue = Venue.query.get(venue_id)
  past_shows = db.session.query(Show, Artist)\
    .join(Artist, Artist.id == Show.artist_id)\
    .filter(Show.venue_id == venue_id, Show.start_time <= datetime.now()).all()
  upcoming_shows = db.session.query(Show, Artist)\
    .join(Artist, Artist.id == Show.artist_id)\
    .filter(Show.venue_id == venue_id, Show.start_time > datetime.now()).all()

  # prepare show data
  past_shows_list = []
  for s, a in past_shows:
      past_shows_list.append({
        'artist_id': a.id,
        'artist_name': a.name,
        'artist_image_link': a.image_link,
        'start_time': s.start_time.strftime("%d/%m/%Y, %H:%M")
      })
  upcoming_shows_list = []
  for s, a in upcoming_shows:
      upcoming_shows_list.append({
        'artist_id': a.id,
        'artist_name': a.name,
        'artist_image_link': a.image_link,
        'start_time': s.start_time.strftime("%d/%m/%Y, %H:%M")
      })

  # combine all data
  data = {
    'id': venue_id,
    'name': venue.name,
    'genres': venue.genres.split(', '),
    'address': venue.address,
    'city': venue.city,
    'state': venue.state,
    'phone': venue.phone,
    'website': venue.website_link,
    'facebook_link': venue.facebook_link,
    'seeking_talent': venue.looking_for_talent,
    'seeking_description': venue.seeking_description,
    'image_link': venue.image_link,
    'past_shows': past_shows_list,
    'upcoming_shows': upcoming_shows_list,
    'past_shows_count': len(past_shows),
    'upcoming_shows_count': len(upcoming_shows)
  }

  return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  # called upon submitting the new artist listing form
  form = VenueForm(request.form, meta={'csrf': False})

  # display error & re-render filled in form if form input is not valid
  if not form.validate():
      flash(form.errors)
      return render_template('forms/new_venue.html', form=form)

  try:
      new_venue = Venue(
        name = form.name.data,
        city = form.city.data,
        state = form.state.data,
        address = form.address.data,
        phone = form.phone.data,
        genres = ', '.join(form.genres.data),
        image_link = form.image_link.data,
        facebook_link = form.facebook_link.data,
        website_link = form.website_link.data,
        looking_for_talent = form.seeking_talent.data,
        seeking_description = form.seeking_description.data
      )
      db.session.add(new_venue)
      db.session.commit()
      # on successful db insert, flash success
      flash('Venue ' + form.name.data + ' was successfully listed!')
  except:
      db.session.rollback()
      # on unsuccessful db insert, flash an error instead
      flash('An error occurred. Venue ' + form.name.data + ' could not be listed.')
  finally:
      db.session.close()

  return render_template('pages/home.html')


@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  venue_name = db.session.query(Venue.name).filter(Venue.id == venue_id).first().name

  try:
    Venue.query.filter_by(id=venue_id).delete()
    db.session.commit()
    flash('Venue ' + venue_name + ' was successfully deleted!')
  except:
    db.session.rollback()
    flash('An error occurred. Venue ' + venue_name + ' could not be deleted.')
  finally:
    db.session.close()

  return jsonify({ 'success': True })

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  # list all artists
  data = db.session.query(Artist.id, Artist.name).all()
  return render_template('pages/artists.html', artists=data)

@app.route('/artists/search', methods=['POST'])
def search_artists():
  search_term = request.form.get('search_term', '')
  matching_artists = db.session.query(Artist).filter(Artist.name.ilike("%{}%".format(search_term))).all()

  # prepare response data
  data = []
  for a in matching_artists:
      num_upcoming_shows = len(db.session.query(Show)\
        .filter(Show.artist_id == a.id, Show.start_time > datetime.now()).all())
      data.append({
        'id': a.id,
        'name': a.name,
        'num_upcoming_shows': num_upcoming_shows
      })

  response={
    "count": len(data),
    "data": data
  }

  return render_template('pages/search_artists.html', results=response, search_term=search_term)

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  # shows the artist page with the given artist_id
  artist = Artist.query.get(artist_id)
  past_shows = db.session.query(Show, Venue)\
    .join(Venue, Venue.id == Show.venue_id)\
    .filter(Show.artist_id == artist_id, Show.start_time <= datetime.now()).all()
  upcoming_shows = db.session.query(Show, Venue)\
    .join(Venue, Venue.id == Show.venue_id)\
    .filter(Show.artist_id == artist_id, Show.start_time > datetime.now()).all()

  # prepare show data
  past_shows_list = []
  for s, v in past_shows:
      past_shows_list.append({
        'venue_id': v.id,
        'venue_name': v.name,
        'venue_image_link': v.image_link,
        'start_time': s.start_time.strftime("%d/%m/%Y, %H:%M")
      })
  upcoming_shows_list = []
  for s, v in upcoming_shows:
      upcoming_shows_list.append({
        'venue_id': v.id,
        'venue_name': v.name,
        'venue_image_link': v.image_link,
        'start_time': s.start_time.strftime("%d/%m/%Y, %H:%M")
      })

  # combine all data
  data = {
    'id': artist_id,
    'name': artist.name,
    'genres': artist.genres.split(', '),
    'city': artist.city,
    'state': artist.state,
    'phone': artist.phone,
    'website': artist.website_link,
    'facebook_link': artist.facebook_link,
    'seeking_venue': artist.looking_for_venues,
    'seeking_description': artist.seeking_description,
    'image_link': artist.image_link,
    'past_shows': past_shows_list,
    'upcoming_shows': upcoming_shows_list,
    'past_shows_count': len(past_shows),
    'upcoming_shows_count': len(upcoming_shows)
  }

  return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  # pre-populate editing form with artist information
  artist = Artist.query.get(artist_id)
  artist.genres = artist.genres.split(', ')
  form = ArtistForm(
    name = artist.name,
    city = artist.city,
    state = artist.state,
    phone = artist.phone,
    genres = artist.genres,
    facebook_link = artist.facebook_link,
    image_link = artist.image_link,
    website_link = artist.website_link,
    seeking_venue = artist.looking_for_venues,
    seeking_description = artist.seeking_description
  )

  return render_template('forms/edit_artist.html', form=form, artist=artist)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  # update artist on form submission
  form = ArtistForm(request.form, meta={'csrf': False})
  artist = Artist.query.get(artist_id)
  # display error & re-render filled in form if form input is not valid
  if not form.validate():
      flash(form.errors)
      return render_template('forms/edit_artist.html', form=form, artist=artist)
  try:
      artist.name = form.name.data
      artist.city = form.city.data
      artist.state = form.state.data
      artist.phone = form.phone.data
      artist.genres = ', '.join(form.genres.data)
      artist.image_link = form.image_link.data
      artist.facebook_link = form.facebook_link.data
      artist.website_link = form.website_link.data
      artist.looking_for_venues = form.seeking_venue.data
      artist.seeking_description = form.seeking_description.data

      db.session.commit()
      flash('Artist ' + form.name.data + ' was successfully updated!')
  except:
      db.session.rollback()
      flash('An error occurred. Artist ' + form.name.data + ' could not be updated.')
  finally:
      db.session.close()

  return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  # pre-populate editing form with venue information
  venue = Venue.query.get(venue_id)
  venue.genres = venue.genres.split(', ')
  form = VenueForm(
    name = venue.name,
    city = venue.city,
    state = venue.state,
    address = venue.address,
    phone = venue.phone,
    genres = venue.genres,
    facebook_link = venue.facebook_link,
    image_link = venue.image_link,
    website_link = venue.website_link,
    seeking_talent = venue.looking_for_talent,
    seeking_description = venue.seeking_description
  )

  return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  # update venue on form submission
  form = VenueForm(request.form, meta={'csrf': False})
  venue = Venue.query.get(venue_id)
  # display error & re-render filled in form if form input is not valid
  if not form.validate():
      flash(form.errors)
      return render_template('forms/edit_venue.html', form=form, venue=venue)
  try:
      venue.name = form.name.data
      venue.city = form.city.data
      venue.state = form.state.data
      venue.address = form.address.data
      venue.phone = form.phone.data
      venue.genres = ', '.join(form.genres.data)
      venue.image_link = form.image_link.data
      venue.facebook_link = form.facebook_link.data
      venue.website_link = form.website_link.data
      venue.looking_for_talent = form.seeking_talent.data
      venue.seeking_description = form.seeking_description.data

      db.session.commit()
      flash('Venue ' + form.name.data + ' was successfully updated!')
  except:
      db.session.rollback()
      flash('An error occurred. Venue ' + form.name.data + ' could not be updated.')
  finally:
      db.session.close()

  return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  # called upon submitting the new artist listing form
  form = ArtistForm(request.form, meta={'csrf': False})

  # display error & re-render filled in form if form input is not valid
  if not form.validate():
      flash(form.errors)
      return render_template('forms/new_artist.html', form=form)

  try:
      new_artist = Artist(
        name = form.name.data,
        city = form.city.data,
        state = form.state.data,
        phone = form.phone.data,
        genres = ', '.join(form.genres.data),
        image_link = form.image_link.data,
        facebook_link = form.facebook_link.data,
        website_link = form.website_link.data,
        looking_for_venues = form.seeking_venue.data,
        seeking_description = form.seeking_description.data
      )
      db.session.add(new_artist)
      db.session.commit()
      # on successful db insert, flash success
      flash('Artist ' + form.name.data + ' was successfully listed!')
  except:
      db.session.rollback()
      # on unsuccessful db insert, flash an error instead
      flash('An error occurred. Artist ' + form.name.data + ' could not be listed.')
  finally:
      db.session.close()

  return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  # displays list of shows at /shows
  shows = db.session.query(Show, Artist, Venue)\
    .join(Artist, Artist.id == Show.artist_id)\
    .join(Venue, Venue.id == Show.venue_id).all()

  # organize data
  data = []
  for s, a, v in shows:
      data.append({
        'venue_id': v.id,
        'venue_name': v.name,
        'artist_id': a.id,
        'artist_name': a.name,
        'artist_image_link': a.image_link,
        'start_time': s.start_time.strftime("%d/%m/%Y, %H:%M")
      })

  return render_template('pages/shows.html', shows=data)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  # called to create new shows in the db, upon submitting new show listing form
  form = ShowForm(request.form, meta={'csrf': False})

  # display error & re-render filled in form if form input is not valid
  if not form.validate():
      flash(form.errors)
      return render_template('forms/new_show.html', form=form)

  try:
      new_show = Show(
        start_time = form.start_time.data,
        artist_id = form.artist_id.data,
        venue_id = form.venue_id.data
      )
      db.session.add(new_show)
      db.session.commit()
      # on successful db insert, flash success
      flash('Show was successfully listed!')
  except:
      db.session.rollback()
      # on unsuccessful db insert, flash an error instead
      flash('An error occurred. Show could not be listed.')
  finally:
      db.session.close()

  return render_template('pages/home.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
