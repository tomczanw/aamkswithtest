import { Result, HttpManagerService } from '../http-manager/http-manager.service';
import { BehaviorSubject } from 'rxjs/BehaviorSubject';
import { Observable } from 'rxjs/Observable';
import { of } from 'rxjs/observable/of';
import { Injectable } from '@angular/core';
import { Library } from './library';
import { NotifierService } from 'angular-notifier';

@Injectable()
export class LibraryService {

  library: Library = new Library('{ }');

  constructor(private httpManager: HttpManagerService, private readonly notifierService: NotifierService) { }

  //** Get library */
  getLibrary(): Observable<Library> {
    return of(this.library);
  }

  /** Get library from database */
  loadLibrary() {
    this.httpManager.get('https://aamks.inf.sgsp.edu.pl/api/library').then((result: Result) => {
      this.library = new Library(JSON.stringify(result.data));
      this.notifierService.notify(result.meta.status, result.meta.details[0]);
    });
  }

  /** Update library in database */
  updateLibrary() {
    this.httpManager.put('https://aamks.inf.sgsp.edu.pl/api/library', JSON.stringify(this.library.toJSON())).then((result: Result) => {
      this.notifierService.notify(result.meta.status, result.meta.details[0]);
    });
  }

}
